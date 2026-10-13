import contextlib
import importlib.util
from pathlib import Path
import tempfile
from threading import Event
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[3]


class RecorderCancellationTests(unittest.TestCase):
    def test_cancel_during_https_preparation_does_not_create_a_draft(self):
        spec = importlib.util.spec_from_file_location("cancel_record_recipe", ROOT / "scripts/record_recipe.py")
        recorder = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(recorder)
        stop = Event()
        stop.set()
        page = Mock()
        page.is_closed.return_value = False
        context = Mock()
        context.new_page.return_value = page
        browser = Mock()
        browser.new_context.return_value = context
        runtime = SimpleNamespace(chromium=SimpleNamespace(launch=lambda **kw: browser))
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "recipe.json"
            with patch.object(recorder, "sync_playwright", lambda: contextlib.nullcontext(runtime)), patch("sys.argv", ["record_recipe.py", "--url", "https://example.invalid/sgind/#/report", "--output", str(output)]):
                with self.assertRaisesRegex(RuntimeError, "RECORDER_CANCELLED"):
                    recorder.main(stop_event=stop)
            self.assertFalse(output.exists())
            page.goto.assert_called_once_with("https://example.invalid/sgind/#/report")
            browser.new_context.assert_called_once_with(accept_downloads=False, service_workers="block")
            context.close.assert_called_once()
            browser.close.assert_called_once()
