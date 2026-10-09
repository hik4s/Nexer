"""Corporate browser owner with revocation monitoring during pending operations."""
import asyncio
from concurrent.futures import ThreadPoolExecutor
from playwright.async_api import async_playwright

from async_browser_bridge import BrowserThread
from corporate_browser import CorporateBrowserPolicy


class MonitoredCorporatePage:
    def __init__(self, system, *, authorize, headless=True,
                 playwright_factory=async_playwright, poll_seconds=0.5):
        if not callable(authorize) or not 0 < poll_seconds <= 1:
            raise RuntimeError("CORPORATE_CONTEXT_UNAVAILABLE")
        self.corporate_policy = CorporateBrowserPolicy(system, authorize=authorize)
        self._bridge = BrowserThread()
        self._monitor_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="nexer-revocation")
        self._closed = False
        self._playwright = None
        self._browser = None
        self._context = None
        self._monitor = None
        try:
            context = self._bridge.run(self._start(playwright_factory, headless))
            proxy = self._bridge.wrap(context)
            self.corporate_policy.install(proxy)
            self._page = proxy.new_page()
            self.corporate_policy.check()
            self._bridge.run(self._start_monitor(poll_seconds))
        except Exception:
            self.close()
            raise RuntimeError("CORPORATE_CONTEXT_UNAVAILABLE") from None

    async def _start(self, factory, headless):
        self._playwright = await factory().start()
        self._browser = await self._playwright.chromium.launch(
            channel="msedge", headless=headless,
            args=["--disable-features=msDownloadsHub"])
        self._context = await self._browser.new_context(
            accept_downloads=True, service_workers="block")
        return self._context

    async def _start_monitor(self, poll_seconds):
        async def monitor():
            while True:
                await asyncio.sleep(poll_seconds)
                try:
                    await asyncio.get_running_loop().run_in_executor(
                        self._monitor_executor, self.corporate_policy.check)
                except RuntimeError:
                    return  # Policy.check closes the context on the owning loop.
        self._monitor = asyncio.create_task(monitor())

    def __getattr__(self, name):
        return getattr(self._page, name)

    @property
    def raw_page(self):
        return self._page

    def is_alive(self):
        return self._bridge.is_alive()

    async def _shutdown(self):
        if self._monitor is not None:
            self._monitor.cancel()
            await asyncio.gather(self._monitor, return_exceptions=True)
        for resource in (self._context, self._browser):
            if resource is not None:
                try:
                    await asyncio.wait_for(resource.close(), timeout=5)
                except Exception:
                    pass
        if self._playwright is not None:
            await asyncio.wait_for(self._playwright.stop(), timeout=45)

    def close(self):
        if self._closed:
            return
        self._closed = True
        try:
            self._bridge.run(self._shutdown())
        finally:
            self._monitor_executor.shutdown(wait=False, cancel_futures=True)
            self._bridge.stop()

    def __repr__(self):
        return "MonitoredCorporatePage()"
