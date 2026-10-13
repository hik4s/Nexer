"""Real monitor/thread bridge with an asynchronous fake browser boundary."""
import asyncio
import importlib.util
import threading
import time
import unittest


class FakeLocator:
    def __init__(self, context):
        self.context = context

    async def click(self, **kwargs):
        await self.context.closed_event.wait()
        raise RuntimeError("synthetic-browser-secret")


class FakeDownloadInfo:
    def __init__(self, context):
        self.context = context

    @property
    def value(self):
        async def wait():
            await self.context.closed_event.wait()
            raise RuntimeError("synthetic-download-secret")
        return wait()


class FakeDownloadWait:
    def __init__(self, context):
        self.context = context

    async def __aenter__(self):
        return FakeDownloadInfo(self.context)

    async def __aexit__(self, *args):
        return False


class FakePage:
    def __init__(self, context):
        self.context = context
        self.url = "https://indicadoresenergisaess.scl.corp/sgind/#/home"

    async def goto(self, *args, **kwargs):
        await self.context.closed_event.wait()
        raise RuntimeError("synthetic-navigation-secret")

    def locator(self, selector):
        return FakeLocator(self.context)

    def expect_download(self, **kwargs):
        return FakeDownloadWait(self.context)


class FakeContext:
    def __init__(self):
        self.closed_event = asyncio.Event()
        self.closed = threading.Event()
        self.pages = []
        self.callbacks = {}

    async def route(self, pattern, callback):
        self.callbacks["route"] = callback

    async def route_web_socket(self, pattern, callback):
        self.callbacks["websocket"] = callback

    def on(self, event, callback):
        self.callbacks[event] = callback

    async def new_page(self):
        page = FakePage(self)
        self.pages.append(page)
        asyncio.create_task(self.callbacks["page"](page))
        return page

    async def close(self):
        self.closed.set()
        self.closed_event.set()


class FakePlaywright:
    def __init__(self):
        self.chromium = self
        self.context = None
        self.stopped = threading.Event()
        self.browser_closed = threading.Event()

    async def start(self):
        return self

    async def launch(self, **kwargs):
        self.launch_options = kwargs
        return self

    async def new_context(self, **kwargs):
        self.context = FakeContext()
        return self.context

    async def close(self):
        self.browser_closed.set()

    async def stop(self):
        self.stopped.set()


class MonitoredCorporatePageTests(unittest.TestCase):
    def create(self):
        self.assertIsNotNone(importlib.util.find_spec("monitored_browser"),
                             "Monitored corporate browser is missing")
        from monitored_browser import MonitoredCorporatePage
        self.active = True
        self.browser = FakePlaywright()
        def authorize():
            if not self.active:
                raise RuntimeError("synthetic-channel-secret")
        page = MonitoredCorporatePage("SGIND", authorize=authorize,
            playwright_factory=lambda: self.browser, poll_seconds=0.02)
        self.addCleanup(page.close)
        return page

    def revoke_soon(self):
        timer = threading.Timer(0.08, lambda: setattr(self, "active", False))
        timer.start()
        self.addCleanup(timer.join)

    def test_monitor_closes_idle_context_after_revocation(self):
        page = self.create()
        self.active = False
        self.assertTrue(self.browser.context.closed.wait(2))
        with self.assertRaisesRegex(RuntimeError, "^CORPORATE_CONTEXT_REVOKED$"):
            page.corporate_policy.check()

    def test_revocation_interrupts_pending_navigation(self):
        page = self.create()
        self.revoke_soon()
        started = time.monotonic()
        with self.assertRaisesRegex(RuntimeError, "^CORPORATE_BROWSER_OPERATION_FAILED$"):
            page.goto("https://indicadoresenergisaess.scl.corp/sgind/#/report", timeout=30000)
        self.assertLess(time.monotonic() - started, 2)
        self.assertTrue(self.browser.context.closed.is_set())

    def test_revocation_interrupts_pending_click(self):
        page = self.create()
        self.revoke_soon()
        with self.assertRaisesRegex(RuntimeError, "^CORPORATE_BROWSER_OPERATION_FAILED$"):
            page.locator("#missing").click(timeout=30000)
        self.assertTrue(self.browser.context.closed.is_set())

    def test_revocation_interrupts_wait_for_download(self):
        page = self.create()
        self.revoke_soon()
        with self.assertRaisesRegex(RuntimeError, "^CORPORATE_BROWSER_OPERATION_FAILED$"):
            with page.expect_download(timeout=30000) as info:
                pass
            info.value
        self.assertTrue(self.browser.context.closed.is_set())

    def test_close_stops_owned_browser_driver_and_thread(self):
        page = self.create()
        page.close()
        page.close()
        self.assertTrue(self.browser.browser_closed.is_set())
        self.assertTrue(self.browser.stopped.is_set())
        self.assertFalse(page.is_alive())

    def test_browser_objects_are_unwrapped_before_passing_back_to_async_api(self):
        from async_browser_bridge import BrowserThread
        bridge = BrowserThread()
        self.addCleanup(bridge.stop)
        class Response:
            pass
        raw_response = Response()
        class Route:
            async def fetch(self):
                return raw_response
            async def fulfill(self, *, response):
                return response is raw_response
        route = bridge.wrap(Route())
        self.assertTrue(route.fulfill(response=route.fetch()),
                        "Async Playwright must receive the owned raw response, not its sync facade")

    def test_shutdown_does_not_wait_forever_for_browser_close(self):
        page = self.create()
        async def stuck():
            await asyncio.Event().wait()
        self.browser.close = stuck
        started = time.monotonic()
        page.close()
        self.assertLess(time.monotonic() - started, 8)
        self.assertTrue(self.browser.stopped.is_set())
        self.assertFalse(page.is_alive())

    def test_invalid_system_does_not_start_an_owned_thread(self):
        from monitored_browser import MonitoredCorporatePage
        before = {thread.ident for thread in threading.enumerate()
                  if thread.name == "nexer-corporate-browser"}
        with self.assertRaises(RuntimeError):
            MonitoredCorporatePage("INVALID", authorize=lambda: None)
        after = {thread.ident for thread in threading.enumerate()
                 if thread.name == "nexer-corporate-browser"}
        self.assertEqual(after, before)

    def test_monitor_revokes_when_callback_executor_is_saturated(self):
        from concurrent.futures import ThreadPoolExecutor
        page = self.create()
        release = threading.Event()
        started = threading.Event()
        async def saturate():
            loop = asyncio.get_running_loop()
            loop.set_default_executor(ThreadPoolExecutor(max_workers=1))
            def callback():
                started.set()
                release.wait(3)
            return asyncio.create_task(asyncio.to_thread(callback))
        page._bridge.run(saturate())
        try:
            self.assertTrue(started.wait(1))
            self.active = False
            self.assertTrue(self.browser.context.closed.wait(0.5),
                            "Revocation must have capacity independent of network callbacks")
        finally:
            release.set()

    def test_browser_launch_suppresses_edge_internal_download_hub(self):
        self.create()
        self.assertIn("--disable-features=msDownloadsHub", self.browser.launch_options["args"])

    def test_slow_authorization_failure_interrupts_pending_operation_and_cleans_threads(self):
        from monitored_browser import MonitoredCorporatePage
        slow = threading.Event()
        entered = threading.Event()
        release = threading.Event()
        browser = FakePlaywright()
        def authorize():
            if slow.is_set():
                entered.set()
                if not release.wait(2):
                    raise RuntimeError("synthetic-channel-timeout")
                raise RuntimeError("synthetic-channel-revoked")
        page = MonitoredCorporatePage("SGIND", authorize=authorize,
            playwright_factory=lambda: browser, poll_seconds=0.02)
        self.addCleanup(page.close)
        slow.set()
        try:
            self.assertTrue(entered.wait(1))
            timer = threading.Timer(0.15, release.set)
            timer.start()
            with self.assertRaisesRegex(RuntimeError, "^CORPORATE_BROWSER_OPERATION_FAILED$"):
                page.locator("#pending").click()
            timer.join()
            self.assertTrue(browser.context.closed.is_set())
        finally:
            release.set()
            page.close()
        self.assertFalse(page.is_alive())
        self.assertTrue(browser.stopped.is_set())

    def test_simultaneous_operations_are_interrupted_and_all_owned_threads_end(self):
        page = self.create()
        completed = []
        barrier = threading.Barrier(5)
        def pending():
            barrier.wait(timeout=2)
            try:
                page.locator("#pending").click()
            except RuntimeError as exc:
                completed.append(str(exc))
        callers = [threading.Thread(target=pending) for _ in range(4)]
        for caller in callers:
            caller.start()
        try:
            barrier.wait(timeout=2)
            self.active = False
            for caller in callers:
                caller.join(timeout=2)
            self.assertTrue(all(not caller.is_alive() for caller in callers))
            self.assertEqual(completed, ["CORPORATE_BROWSER_OPERATION_FAILED"] * 4)
        finally:
            page.close()
            for caller in callers:
                caller.join(timeout=2)
        self.assertFalse(page.is_alive())

    def test_repeated_start_close_does_not_retain_owned_threads(self):
        def owned():
            return {thread.ident for thread in threading.enumerate()
                    if thread.name.startswith(("nexer-corporate-browser", "nexer-revocation"))}
        before = owned()
        for _ in range(3):
            self.create().close()
        deadline = time.monotonic() + 2
        while owned() != before and time.monotonic() < deadline:
            time.sleep(0.01)
        self.assertEqual(owned(), before)
