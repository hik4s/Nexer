import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from main import build_worker


class WorkerAppBootstrapTests(unittest.TestCase):
    def test_build_worker_starts_browser_and_page_factory_uses_execution_workspace(self):
        browser = Mock()
        page = object()
        browser.create_page.return_value = page

        with patch("main.WorkerService"), patch("main.WorkerExecutionProcessor"), patch("main.WorkerLoop"):
            app = build_worker(browser_manager=browser)

        browser.start.assert_called_once()
        self.assertIs(app.browser_manager, browser)
        self.assertIsNotNone(app.loop)

    def test_page_factory_restores_saved_session_state(self):
        browser = Mock()
        browser.create_page.return_value = object()
        session_store = Mock()
        session_store.load.return_value = {"cookies": [], "origins": []}

        with patch("main.SessionStateStore", return_value=session_store), patch(
            "main.WorkerService"
        ), patch("main.WorkerExecutionProcessor") as processor, patch("main.WorkerLoop"):
            build_worker(browser_manager=browser)

        page_factory = processor.call_args.kwargs["page_factory"]
        execution = Mock(id=12)
        item = Mock(id=3)
        recipe = {"authentication": {"session_ref": "portal-a"}}

        page_factory(execution, item, recipe)

        session_store.load.assert_called_once_with("portal-a")
        browser.create_page.assert_called_once_with(
            "12-3",
            storage_state={"cookies": [], "origins": []},
        )


if __name__ == "__main__":
    unittest.main()
