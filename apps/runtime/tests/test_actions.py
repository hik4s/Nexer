import tempfile
import unittest
from pathlib import Path


from actions import ActionExecutionError, create_default_registry
from context import ExecutionContext


class FakeLocator:
    def __init__(self):
        self.calls = []

    def click(self):
        self.calls.append(("click",))

    def fill(self, value):
        self.calls.append(("fill", value))

    def select_option(self, value):
        self.calls.append(("select_option", value))

    def wait_for(self, state="visible", timeout=30000):
        self.calls.append(("wait_for", state, timeout))

    def is_visible(self):
        self.calls.append(("is_visible",))
        return True


class FakePage:
    def __init__(self):
        self.urls = []
        self.locators = {}
        self.pages = [self]
        self.download_count = 0

    def goto(self, url, wait_until="domcontentloaded", timeout=30000):
        self.urls.append((url, wait_until, timeout))

    def locator(self, selector):
        locator = self.locators.setdefault(selector, FakeLocator())
        return locator


class ActionTests(unittest.TestCase):
    def setUp(self):
        self.page = FakePage()
        self.events = []
        self.context = ExecutionContext(
            page=self.page,
            variables={"period_start": "2026-10-01"},
            downloads_dir=Path(tempfile.mkdtemp()),
            dry_run=False,
            emit=self.events.append,
        )
        self.registry = create_default_registry()

    def test_navigate_click_fill_and_select_actions(self):
        self.registry.execute(
            "navigate",
            {"id": "open", "url": "https://example.test"},
            self.context,
        )
        self.registry.execute(
            "click",
            {"id": "click", "selector": "#run"},
            self.context,
        )
        self.registry.execute(
            "fill",
            {
                "id": "fill",
                "selector": "#start",
                "value": "{{period_start}}",
            },
            self.context,
        )
        self.registry.execute(
            "select",
            {
                "id": "select",
                "selector": "#company",
                "value": "001",
            },
            self.context,
        )

        self.assertEqual(
            self.page.urls[0][0],
            "https://example.test",
        )
        self.assertEqual(
            self.page.locator("#run").calls,
            [("click",)],
        )
        self.assertEqual(
            self.page.locator("#start").calls,
            [("fill", "2026-10-01")],
        )
        self.assertEqual(
            self.page.locator("#company").calls,
            [("select_option", "001")],
        )
        self.assertGreaterEqual(len(self.events), 4)

    def test_wait_for_any_uses_first_available_selector(self):
        self.page.locators["#slow"] = FakeLocator()
        self.page.locators["#ready"] = FakeLocator()

        self.registry.execute(
            "wait_for_any",
            {
                "id": "wait",
                "selectors": ["#slow", "#ready"],
            },
            self.context,
        )

        self.assertTrue(
            any(call[0] == "is_visible" for call in self.page.locator("#ready").calls)
        )

    def test_validate_file_rejects_empty_file(self):
        empty = self.context.downloads_dir / "report.xlsx"
        empty.write_bytes(b"")

        with self.assertRaises(ActionExecutionError):
            self.registry.execute(
                "validate_file",
                {
                    "id": "validate",
                    "path": str(empty),
                    "min_size": 1,
                    "extensions": [".xlsx"],
                },
                self.context,
            )

    def test_dry_run_does_not_touch_page(self):
        context = ExecutionContext(
            page=self.page,
            variables={},
            downloads_dir=self.context.downloads_dir,
            dry_run=True,
            emit=self.events.append,
        )

        self.registry.execute(
            "click",
            {"id": "click", "selector": "#run"},
            context,
        )

        self.assertEqual(self.page.locator("#run").calls, [])


if __name__ == "__main__":
    unittest.main()
