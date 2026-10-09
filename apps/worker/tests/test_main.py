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

    def test_page_factory_discards_saved_session_state(self):
        browser = Mock()
        browser.create_page.return_value = object()
        session_store = Mock()
        session_store.load.return_value = {"cookies": [], "origins": []}

        with patch("session_store.SessionStateStore", return_value=session_store), patch(
            "main.WorkerService"
        ), patch("main.WorkerExecutionProcessor") as processor, patch("main.WorkerLoop"):
            build_worker(browser_manager=browser)

        page_factory = processor.call_args.kwargs["page_factory"]
        execution = Mock(id=12)
        item = Mock(id=3)
        recipe = {"authentication": {"session_ref": "portal-a"}}

        page_factory(execution, item, recipe)

        session_store.load.assert_not_called()
        browser.create_page.assert_called_once_with("12-3")



    def test_corporate_factory_uses_restricted_manager_method(self):
        class Manager:
            def start(self):
                pass
            def create_monitored_corporate_page(self, system, *, authorize):
                authorize()
                return {"system": system, "restricted": True}
        from unittest.mock import patch
        with patch("main.WorkerService"), patch("main.WorkerExecutionProcessor") as processor, patch("main.WorkerLoop"):
            build_worker(browser_manager=Manager())
        self.assertIn("corporate_page_factory", processor.call_args.kwargs)
        calls = []
        factory = processor.call_args.kwargs["corporate_page_factory"]
        result = factory("IQOS", lambda: calls.append("authorized"))
        self.assertEqual(result, {"system": "IQOS", "restricted": True})
        self.assertEqual(calls, ["authorized"])


if __name__ == "__main__":
    unittest.main()
