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
        storage_state: str | Path | None = None,
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
        storage_state: str | Path | None = None,
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

    @property
    def raw_page(self):
        return self._page


def _safe_execution_id(execution_id: str | int) -> str:
    value = str(execution_id)
    if not re.fullmatch(r"[A-Za-z0-9_-]+", value):
        raise BrowserManagerError("UNSAFE_EXECUTION_ID")
    return value
