"""Real Edge monitor tests with loopback-only synthetic responses."""
import asyncio
import os
import tempfile
import threading
import time
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

from playwright.async_api import async_playwright
from monitored_browser import MonitoredCorporatePage
from corporate_auth import authenticate_corporate
from test_corporate_edge_fixture import HTML, Handler, Client


DOCUMENT = HTML.replace(b"</body>", b'<button id="normal">No download</button>'
                       b'<a id="download" download="report.txt" href="/sgind/export">Download</a></body>')


class MonitoredHandler(Handler):
    def do_GET(self):
        if self.path in {"/slow", "/sgind/slow"}:
            self.server.started.set()
            self.server.release.wait(10)
        if self.path in {"/download", "/sgind/export"}:
            body = b"synthetic-report"
            self.send_response(200)
            self.send_header("Content-Type", "application/octet-stream")
            self.send_header("Content-Disposition", 'attachment; filename="report.txt"')
        else:
            body = DOCUMENT
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        try:
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            pass


class AsyncFixtureContext:
    def __init__(self, raw, fixture):
        self.raw, self.fixture = raw, fixture
        raw.on("close", lambda *args: fixture.closed.set())

    def __getattr__(self, name):
        return getattr(self.raw, name)

    async def route(self, pattern, handler):
        async def bridge(route):
            context = self
            class FixtureRoute:
                request = route.request
                async def fetch(self, **kwargs):
                    if route.request.url.startswith(context.fixture.base_url + "/sgind/"):
                        return await route.fetch(**kwargs)
                    path = urlsplit(route.request.url).path
                    endpoint = "/download" if path.endswith("/export") else (
                        "/slow" if path.endswith("/slow") else "/login")
                    return await context.raw.request.get(
                        context.fixture.base_url + endpoint, **kwargs)
                async def fulfill(self, **kwargs):
                    await route.fulfill(**kwargs)
                async def continue_(self):
                    await route.continue_()
                async def abort(self, *args):
                    await route.abort(*args)
            await handler(FixtureRoute())
        await self.raw.route(pattern, bridge)


class AsyncFixturePlaywright:
    def __init__(self, base_url):
        self.base_url = base_url
        self.closed = threading.Event()
        self.chromium = self
        self.playwright = None
        self.browser = None

    async def start(self):
        self.playwright = await async_playwright().start()
        return self

    async def launch(self, **kwargs):
        self.browser = await self.playwright.chromium.launch(**kwargs)
        return self

    async def new_context(self, **kwargs):
        return AsyncFixtureContext(await self.browser.new_context(**kwargs), self)

    async def close(self):
        await self.browser.close()

    async def stop(self):
        await self.playwright.stop()



def trusted_fixture(base_url):
    """Test-only trusted adapter for a real HTTP loopback origin.

    Production policies stay pinned to corporate HTTPS. Synthetic downloads
    use a real loopback origin, avoiding invented TLS state in a mocked domain.
    """
    from contextlib import ExitStack, contextmanager
    from dataclasses import replace
    from unittest.mock import patch
    import corporate_auth
    import corporate_browser
    import corporate_guard
    definition = replace(corporate_auth.get_login_definition("SGIND"),
        login_url=base_url + "/sgind/#/login", home_url=base_url + "/sgind/#/home")
    def validate(system, url):
        if system != "SGIND" or not isinstance(url, str) or not url.startswith(base_url + "/sgind/"):
            raise RuntimeError("CORPORATE_DESTINATION_FORBIDDEN")
    @contextmanager
    def scoped():
        with ExitStack() as stack:
            for module in (corporate_auth, corporate_browser, corporate_guard):
                stack.enter_context(patch.object(module, "get_login_definition", lambda system: definition))
                stack.enter_context(patch.object(module, "validate_corporate_url", validate))
            yield definition
    return scoped()

@unittest.skipUnless(os.getenv("NEXER_RUN_CORPORATE_FIXTURE_E2E") == "1",
                     "Set NEXER_RUN_CORPORATE_FIXTURE_E2E=1 for monitored Edge fixtures")
class MonitoredEdgeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), MonitoredHandler)
        cls.server.started = threading.Event()
        cls.server.release = threading.Event()
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.release.set()
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()

    def setUp(self):
        self.active = True
        self.base_url = f"http://127.0.0.1:{self.server.server_port}"
        scope = trusted_fixture(self.base_url)
        self.definition = scope.__enter__()
        self.addCleanup(scope.__exit__, None, None, None)
        self.fixture = AsyncFixturePlaywright(f"http://127.0.0.1:{self.server.server_port}")
        def authorize():
            if not self.active:
                raise RuntimeError("synthetic-revocation")
        self.page = MonitoredCorporatePage("SGIND", authorize=authorize,
            playwright_factory=lambda: self.fixture, poll_seconds=0.05)
        self.addCleanup(self.page.close)
        self.page.goto(self.definition.login_url)

    def revoke_soon(self):
        timer = threading.Timer(0.3, lambda: setattr(self, "active", False))
        timer.start()
        self.addCleanup(timer.join)

    def test_real_login_and_download_work_through_async_facade(self):
        authenticate_corporate(self.page, Client(), 1, "SGIND", timeout_ms=5000)
        with tempfile.TemporaryDirectory() as directory:
            with self.page.expect_download(timeout=5000) as info:
                self.page.locator("#download").click(timeout=5000)
            target = Path(directory) / "report.txt"
            info.value.save_as(str(target))
            self.assertEqual(target.read_bytes(), b"synthetic-report")
        self.assertEqual(self.page.url,
                         self.definition.home_url)

    def test_real_idle_context_closes_without_next_worker_action(self):
        self.active = False
        self.assertTrue(self.fixture.closed.wait(3))

    def test_real_pending_click_is_interrupted_by_monitor(self):
        self.revoke_soon()
        started = time.monotonic()
        with self.assertRaisesRegex(RuntimeError, "^CORPORATE_BROWSER_OPERATION_FAILED$"):
            self.page.locator("#missing").click(timeout=30000)
        self.assertLess(time.monotonic() - started, 4)
        self.assertTrue(self.fixture.closed.wait(1))

    def test_real_pending_download_is_interrupted_by_monitor(self):
        self.revoke_soon()
        started = time.monotonic()
        with self.assertRaisesRegex(RuntimeError, "^CORPORATE_BROWSER_OPERATION_FAILED$"):
            with self.page.expect_download(timeout=30000) as info:
                self.page.locator("#normal").click(timeout=5000)
            info.value
        self.assertLess(time.monotonic() - started, 4)
        self.assertTrue(self.fixture.closed.wait(1))

    def test_real_pending_navigation_is_interrupted_by_monitor(self):
        self.server.started.clear()
        self.server.release.clear()
        self.addCleanup(self.server.release.set)
        self.revoke_soon()
        started = time.monotonic()
        with self.assertRaisesRegex(RuntimeError, "^CORPORATE_BROWSER_OPERATION_FAILED$"):
            self.page.goto(self.base_url + "/sgind/slow", timeout=30000)
        self.assertTrue(self.server.started.is_set())
        self.assertLess(time.monotonic() - started, 4)
        self.assertTrue(self.fixture.closed.wait(1))
