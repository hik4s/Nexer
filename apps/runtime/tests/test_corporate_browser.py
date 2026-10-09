import importlib.util
import unittest
from types import SimpleNamespace
from browser_manager import BrowserManager


class Context:
    def __init__(self):
        self.closed = False
        self.handlers = {}
        self.events = {}
        self.pages = []

    def route(self, pattern, handler):
        self.handlers["http"] = handler

    def route_web_socket(self, pattern, handler):
        self.handlers["websocket"] = handler

    def on(self, event, handler):
        self.events[event] = handler

    def new_page(self):
        page = SimpleNamespace(context=self)
        self.pages.append(page)
        if "page" in self.events:
            self.events["page"](page)
        return page

    def close(self):
        self.closed = True


class Route:
    def __init__(self, url, *, status=200, parent=None):
        self.request = SimpleNamespace(url=url, resource_type="document",
                                       frame=SimpleNamespace(parent_frame=parent))
        self.response = SimpleNamespace(status=status, dispose=lambda: None)
        self.fetches = []
        self.fulfilled = False
        self.aborted = False

    def fetch(self, **kwargs):
        self.fetches.append(kwargs)
        return self.response

    def fulfill(self, **kwargs):
        self.fulfilled = True

    def abort(self, *args):
        self.aborted = True


class CorporateBrowserTests(unittest.TestCase):
    def policy(self, context, authorize=lambda: None):
        self.assertIsNotNone(importlib.util.find_spec("corporate_browser"),
                             "Corporate browser policy is missing")
        from corporate_browser import CorporateBrowserPolicy
        policy = CorporateBrowserPolicy("SGIND", authorize=authorize)
        policy.install(context)
        return policy

    def test_allowed_request_is_fetched_without_redirects_or_retries(self):
        context = Context()
        policy = self.policy(context)
        route = Route("https://indicadoresenergisaess.scl.corp/sgind/api/report")
        context.handlers["http"](route)
        self.assertEqual(route.fetches, [{"max_redirects": 0, "max_retries": 0, "timeout": 5000}])
        self.assertTrue(route.fulfilled)
        self.assertFalse(context.closed)
        policy.check()

    def test_external_and_cross_system_requests_close_context_before_network(self):
        for url in ("https://evil.example/collect",
                    "https://indicadoresenergisaess.scl.corp/iqos/api",
                    "http://indicadoresenergisaess.scl.corp/sgind/",
                    "file:///C:/secret"):
            context = Context()
            policy = self.policy(context)
            route = Route(url)
            context.handlers["http"](route)
            self.assertEqual(route.fetches, [])
            self.assertTrue(route.aborted)
            self.assertTrue(context.closed)
            with self.assertRaisesRegex(RuntimeError, "^CORPORATE_CONTEXT_REVOKED$"):
                policy.check()

    def test_http_redirect_is_not_followed_or_fulfilled(self):
        context = Context()
        self.policy(context)
        route = Route("https://indicadoresenergisaess.scl.corp/sgind/api", status=302)
        context.handlers["http"](route)
        self.assertTrue(context.closed)
        self.assertTrue(route.aborted)
        self.assertFalse(route.fulfilled)
        self.assertEqual(len(route.fetches), 1)

    def test_expired_authorization_prevents_network(self):
        def expired():
            raise ValueError("synthetic-secret-canary")
        context = Context()
        policy = self.policy(context, expired)
        route = Route("https://indicadoresenergisaess.scl.corp/sgind/api")
        context.handlers["http"](route)
        self.assertEqual(route.fetches, [])
        self.assertTrue(context.closed)
        with self.assertRaisesRegex(RuntimeError, "^CORPORATE_CONTEXT_REVOKED$"):
            policy.check()

    def test_iframe_document_is_denied(self):
        context = Context()
        self.policy(context)
        route = Route("https://indicadoresenergisaess.scl.corp/sgind/frame", parent=object())
        context.handlers["http"](route)
        self.assertEqual(route.fetches, [])
        self.assertTrue(context.closed)

    def test_second_page_revokes_context(self):
        context = Context()
        self.policy(context)
        context.new_page()
        self.assertFalse(context.closed)
        context.new_page()
        self.assertTrue(context.closed)

    def test_websocket_revokes_without_connecting_and_next_check_closes_context(self):
        context = Context()
        policy = self.policy(context)
        socket = SimpleNamespace(closed=False)
        def close(**kwargs):
            socket.closed = True
        socket.close = close
        context.handlers["websocket"](socket)
        with self.assertRaisesRegex(RuntimeError, "^CORPORATE_CONTEXT_REVOKED$"):
            policy.check()
        self.assertTrue(context.closed)

    def test_policy_setup_failure_closes_context(self):
        context = Context()
        def broken(*args):
            raise ValueError("synthetic-secret-canary")
        context.route_web_socket = broken
        with self.assertRaisesRegex(RuntimeError, "^CORPORATE_CONTEXT_UNAVAILABLE$"):
            self.policy(context)
        self.assertTrue(context.closed)

    def test_factory_installs_restrictions_before_creating_page(self):
        self.assertTrue(hasattr(BrowserManager, "create_corporate_page"),
                        "Restricted corporate page factory is missing")
        context = Context()
        options = []
        def create(**kwargs):
            options.append(kwargs)
            return context
        manager = BrowserManager()
        manager._browser = SimpleNamespace(new_context=create)
        handle = manager.create_corporate_page("SGIND", authorize=lambda: None)
        self.assertEqual(options, [{"accept_downloads": True, "service_workers": "block"}])
        self.assertIn("http", context.handlers)
        self.assertIn("websocket", context.handlers)
        self.assertEqual(len(context.pages), 1)
        handle.close()
        self.assertTrue(context.closed)

    def test_document_response_restricts_frames_workers_plugins_and_form_actions(self):
        context = Context()
        self.policy(context)
        route = Route("https://indicadoresenergisaess.scl.corp/sgind/")
        route.response.headers = {"content-security-policy": "default-src 'self'"}
        headers = []
        def fulfill(**kwargs):
            headers.append(kwargs.get("headers", {}))
        route.fulfill = fulfill
        context.handlers["http"](route)
        self.assertEqual(len(headers), 1)
        value = headers[0].get("content-security-policy", "")
        self.assertIn("default-src 'self', ", value)
        self.assertIn("frame-src 'none'", value)
        self.assertIn("worker-src 'none'", value)
        self.assertIn("object-src 'none'", value)
        self.assertIn("base-uri 'none'", value)
        self.assertIn("form-action https://indicadoresenergisaess.scl.corp/sgind/", value)
