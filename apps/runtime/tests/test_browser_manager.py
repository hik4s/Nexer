import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from browser_manager import BrowserManager


class FakeBrowser:
    def __init__(self):
        self.contexts = []
        self.closed = False

    def new_context(self, **kwargs):
        self.contexts.append(kwargs)
        return {"settings": kwargs}

    def close(self):
        self.closed = True


class FakeBrowserType:
    def __init__(self, browser):
        self.browser = browser
        self.launch_calls = []

    def launch(self, **kwargs):
        self.launch_calls.append(kwargs)
        return self.browser


class FakePlaywright:
    def __init__(self, browser):
        self.browser = browser
        self.chromium = FakeBrowserType(browser)
        self.stopped = False

    def stop(self):
        self.stopped = True


class FakePlaywrightHandle:
    def __init__(self, playwright):
        self.playwright = playwright

    def start(self):
        return self.playwright


class BrowserManagerTests(unittest.TestCase):
    def test_starts_edge_with_downloads_enabled(self):
        browser = FakeBrowser()
        playwright = FakePlaywright(browser)

        with tempfile.TemporaryDirectory() as tmp:
            manager = BrowserManager(
                headless=False,
                temp_root=Path(tmp),
            )

            with patch(
                "browser_manager.sync_playwright",
                return_value=FakePlaywrightHandle(playwright),
            ):
                manager.start()
                context = manager.create_context("execution-1")
                manager.close()
                self.assertTrue((Path(tmp) / "execution-1").is_dir())

        self.assertEqual(
            playwright.chromium.launch_calls,
            [{"channel": "msedge", "headless": False}],
        )
        self.assertTrue(
            browser.contexts[0]["accept_downloads"]
        )
        self.assertTrue(browser.closed)
        self.assertTrue(playwright.stopped)
        self.assertIsNotNone(context)


    def test_execution_workspace_rejects_path_traversal(self):
        browser = FakeBrowser()
        playwright = FakePlaywright(browser)

        with tempfile.TemporaryDirectory() as tmp:
            manager = BrowserManager(
                headless=True,
                temp_root=Path(tmp),
            )
            with patch(
                "browser_manager.sync_playwright",
                return_value=FakePlaywrightHandle(playwright),
            ):
                manager.start()
                with self.assertRaisesRegex(
                    Exception,
                    "UNSAFE_EXECUTION_ID",
                ):
                    manager.create_context("../outside")

                manager.close()


    def test_create_page_closes_its_context(self):
        browser = FakeBrowser()
        playwright = FakePlaywright(browser)

        class FakeContext:
            def __init__(self):
                self.closed = False
                self.pages = []

            def new_page(self):
                page = object()
                self.pages.append(page)
                return page

            def close(self):
                self.closed = True

        context = FakeContext()
        browser.new_context = lambda **_kwargs: context

        with tempfile.TemporaryDirectory() as tmp:
            manager = BrowserManager(
                headless=True,
                temp_root=Path(tmp),
            )
            with patch(
                "browser_manager.sync_playwright",
                return_value=FakePlaywrightHandle(playwright),
            ):
                manager.start()
                handle = manager.create_page("execution-3")
                handle.close()
                manager.close()

        self.assertTrue(context.closed)

    def test_storage_state_is_optional_and_never_written_to_logs(self):
        browser = FakeBrowser()
        playwright = FakePlaywright(browser)

        with tempfile.TemporaryDirectory() as tmp:
            manager = BrowserManager(
                headless=True,
                temp_root=Path(tmp),
            )
            with patch(
                "browser_manager.sync_playwright",
                return_value=FakePlaywrightHandle(playwright),
            ):
                manager.start()
                manager.create_context(
                    "execution-2",
                    storage_state="C:/sensitive/state.json",
                )

        self.assertEqual(
            browser.contexts[0]["storage_state"],
            "C:/sensitive/state.json",
        )
        self.assertNotIn(
            "sensitive/state.json",
            repr(manager),
        )


if __name__ == "__main__":
    unittest.main()
