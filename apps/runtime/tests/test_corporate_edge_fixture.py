"""Opt-in real Edge tests with loopback-only synthetic HTTP responses.

The corporate hostname is intercepted. No corporate network or real credential
is contacted: route.fetch is replaced only at the external HTTP test boundary.
"""
import os
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread

from browser_manager import BrowserManager
from corporate_auth import authenticate_corporate
from playwright.sync_api import sync_playwright


HTML = b"""<!doctype html><html><body>
<form id="idFormLogin"><input name="cre_username">
<input name="cre_password" type="password">
<button type="submit">Logar</button></form>
<script>
document.querySelector('form').addEventListener('submit', e => {
 e.preventDefault();
 document.querySelector('form').remove();
 history.replaceState(null, '', '#/home');
 const home = document.createElement('app-home-page');
 home.textContent = 'Synthetic home'; home.style.display = 'block';
 document.body.appendChild(home);
});
</script></body></html>"""


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_GET(self):
        if self.path == "/redirect":
            self.send_response(302)
            self.send_header("Location", "https://external.invalid/")
            self.end_headers()
        else:
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(HTML)))
            self.end_headers()
            self.wfile.write(HTML)


class FixtureContext:
    def __init__(self, raw, base_url, fetched):
        self.raw, self.base_url, self.fetched = raw, base_url, fetched
        self.redirect = False

    def __getattr__(self, name):
        return getattr(self.raw, name)

    def route(self, pattern, handler):
        def bridge(route):
            context = self
            class FixtureRoute:
                request = route.request
                def fetch(self, **kwargs):
                    context.fetched.append(route.request.url)
                    path = "/redirect" if context.redirect else "/login"
                    return context.raw.request.get(context.base_url + path, **kwargs)
                def fulfill(self, **kwargs):
                    route.fulfill(**kwargs)
                def abort(self, *args):
                    route.abort(*args)
            handler(FixtureRoute())
        self.raw.route(pattern, bridge)


class FixtureBrowser:
    def __init__(self, browser, base_url):
        self.browser, self.base_url = browser, base_url
        self.fetched = []
        self.context = None

    def new_context(self, **kwargs):
        self.context = FixtureContext(self.browser.new_context(**kwargs),
                                      self.base_url, self.fetched)
        return self.context


class Client:
    def __init__(self):
        self.copies = []

    def resolve(self, execution_id, system):
        values = {"username": "synthetic-user", "password": "synthetic-password"}
        self.copies.append(values)
        return values


@unittest.skipUnless(os.getenv("NEXER_RUN_CORPORATE_FIXTURE_E2E") == "1",
                     "Set NEXER_RUN_CORPORATE_FIXTURE_E2E=1 for local synthetic Edge tests")
class CorporateEdgeFixtureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        cls.thread = Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.playwright = sync_playwright().start()
        cls.browser = cls.playwright.chromium.launch(channel="msedge", headless=True)

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.playwright.stop()
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()

    def setUp(self):
        self.adapter = FixtureBrowser(self.browser,
            f"http://127.0.0.1:{self.server.server_port}")
        self.manager = BrowserManager()
        self.manager._browser = self.adapter
        self.handle = self.manager.create_corporate_page("SGIND", authorize=lambda: None)

    def tearDown(self):
        self.handle.close()

    def test_login_uses_real_dom_and_home_evidence_then_blocks_external_fetch(self):
        client = Client()
        authenticate_corporate(self.handle, client, 1, "SGIND", timeout_ms=5000)
        self.assertEqual(self.handle.url,
                         "https://indicadoresenergisaess.scl.corp/sgind/#/home")
        self.assertTrue(self.handle.locator("app-home-page").is_visible())
        self.assertEqual(self.handle.locator("form").count(), 0)
        self.assertTrue(all(values == {} for values in client.copies))
        fetched_before = len(self.adapter.fetched)
        try:
            self.handle.evaluate("fetch('https://external.invalid/collect').catch(() => {})")
        except Exception:
            pass  # Policy closes the context, interrupting the evaluate call.
        try:
            self.handle.wait_for_timeout(100)
        except Exception:
            pass
        self.assertTrue(self.handle.raw_page.is_closed())
        self.assertEqual(len(self.adapter.fetched), fetched_before)

    def test_http_redirect_never_reaches_its_target(self):
        self.adapter.context.redirect = True
        with self.assertRaises(Exception):
            self.handle.goto("https://indicadoresenergisaess.scl.corp/sgind/#/login")
        try:
            self.handle.wait_for_timeout(100)
        except Exception:
            pass
        self.assertTrue(self.handle.raw_page.is_closed())
        self.assertEqual(self.adapter.fetched,
                         ["https://indicadoresenergisaess.scl.corp/sgind/"])

    def test_websocket_is_denied_in_real_browser(self):
        self.handle.goto("https://indicadoresenergisaess.scl.corp/sgind/#/login")
        try:
            self.handle.evaluate("new WebSocket('wss://external.invalid/socket')")
            self.handle.wait_for_timeout(100)
        except Exception:
            pass
        try:
            self.handle.wait_for_timeout(100)
        except Exception:
            pass
        with self.assertRaisesRegex(RuntimeError, "^CORPORATE_CONTEXT_REVOKED$"):
            self.handle.corporate_policy.check()
        self.assertTrue(self.handle.raw_page.is_closed())
