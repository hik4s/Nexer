from pathlib import Path
import re

from playwright.sync_api import sync_playwright


class BrowserManagerError(RuntimeError):
    """Raised when the browser lifecycle cannot be managed safely."""


class BrowserManager:
    def __init__(
        self,
        *,
        headless: bool = True,
        temp_root: Path = Path("./downloads"),
    ):
        self.headless = headless
        self.temp_root = Path(temp_root)
        self._playwright = None
        self._browser = None

    def start(self) -> None:
        if self._browser is not None:
            return

        try:
            self._playwright = sync_playwright().start()
            self._browser = self._playwright.chromium.launch(
                channel="msedge",
                headless=self.headless,
            )
        except Exception as exc:
            self.close()
            raise BrowserManagerError("BROWSER_START_FAILED") from exc

    def create_context(
        self,
        execution_id: str | int,
        *,
        storage_state: str | Path | dict | None = None,
    ):
        if self._browser is None:
            raise BrowserManagerError("BROWSER_NOT_STARTED")

        safe_execution_id = _safe_execution_id(execution_id)
        execution_root = self.temp_root / safe_execution_id
        execution_root.mkdir(parents=True, exist_ok=True)

        options = {
            "accept_downloads": True,
        }
        if storage_state is not None:
            options["storage_state"] = str(storage_state)

        try:
            return self._browser.new_context(**options)
        except Exception as exc:
            raise BrowserManagerError("BROWSER_CONTEXT_FAILED") from exc

    def create_page(
        self,
        execution_id: str | int,
        *,
        storage_state: str | Path | dict | None = None,
    ):
        context = self.create_context(
            execution_id,
            storage_state=storage_state,
        )
        try:
            page = context.new_page()
        except Exception as exc:
            context.close()
            raise BrowserManagerError("BROWSER_PAGE_FAILED") from exc
        return BrowserPageHandle(context=context, page=page)



    def create_monitored_corporate_page(self, system, *, authorize):
        from monitored_browser import MonitoredCorporatePage
        return MonitoredCorporatePage(system, authorize=authorize, headless=self.headless)

    def create_corporate_page(self, system, *, authorize):
        """Fresh restricted context; no storage state, traces or persistent profile."""
        from corporate_browser import CorporateBrowserPolicy

        if self._browser is None:
            raise BrowserManagerError("BROWSER_NOT_STARTED")
        policy = CorporateBrowserPolicy(system, authorize=authorize)
        context = None
        try:
            context = self._browser.new_context(
                accept_downloads=True, service_workers="block")
            policy.install(context)
            page = context.new_page()
            policy.check()
            handle = BrowserPageHandle(context=context, page=page)
            handle.corporate_policy = policy
            return handle
        except Exception:
            if context is not None:
                try:
                    context.close()
                except Exception:
                    pass
            raise BrowserManagerError("CORPORATE_CONTEXT_UNAVAILABLE") from None

    def close(self) -> None:
        browser = self._browser
        playwright = self._playwright
        self._browser = None
        self._playwright = None

        if browser is not None:
            try:
                browser.close()
            except Exception:
                pass

        if playwright is not None:
            try:
                playwright.stop()
            except Exception:
                pass

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, *_args):
        self.close()

    def __repr__(self) -> str:
        return (
            f"BrowserManager(headless={self.headless!r}, "
            f"temp_root={str(self.temp_root)!r})"
        )


class BrowserPageHandle:
    def __init__(self, *, context, page):
        self._context = context
        self._page = page

    def __getattr__(self, name):
        return getattr(self._page, name)

    def close(self) -> None:
        self._context.close()

    def storage_state(self, **kwargs):
        return self._context.storage_state(**kwargs)

    @property
    def raw_page(self):
        return self._page


def _safe_execution_id(execution_id: str | int) -> str:
    value = str(execution_id)
    if not re.fullmatch(r"[A-Za-z0-9_-]+", value):
        raise BrowserManagerError("UNSAFE_EXECUTION_ID")
    return value
