import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from main import WorkerApp, build_worker


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


if __name__ == "__main__":
    unittest.main()
