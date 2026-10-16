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
            page.goto.assert_called_once_with("https://example.invalid/sgind/#/report", wait_until="domcontentloaded")
            browser.new_context.assert_called_once_with(accept_downloads=False, service_workers="block")
            context.close.assert_called_once()
            browser.close.assert_called_once()

    def test_transient_navigation_during_search_does_not_terminate_recording(self):
        """Search/loading may replace an execution context while recording remains alive."""
        from playwright.sync_api import Error as PlaywrightError
        spec = importlib.util.spec_from_file_location("navigation_record_recipe", ROOT / "scripts/record_recipe.py")
        recorder = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(recorder)
        finish = Event()
        page = Mock()
        page.is_closed.return_value = False
        attempts = []
        def simulate_loading(_duration):
            attempts.append(True)
            if len(attempts) == 1:
                raise PlaywrightError("Execution context was destroyed, most likely because of a navigation")
            finish.set()
        page.wait_for_timeout.side_effect = simulate_loading
        context = Mock()
        context.pages = [page]
        context.new_page.return_value = page
        browser = Mock()
        browser.new_context.return_value = context
        runtime = SimpleNamespace(chromium=SimpleNamespace(launch=lambda **kw: browser))
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "recipe.json"
            with patch.object(recorder, "sync_playwright", lambda: contextlib.nullcontext(runtime)), patch("sys.argv", ["record_recipe.py", "--url", "http://127.0.0.1/report", "--output", str(output)]):
                with self.assertRaisesRegex(RuntimeError, "RECORDER_EMPTY"):
                    recorder.main(finish_event=finish)
            self.assertEqual(len(attempts), 2, "a transient page navigation must not end the recording")
            self.assertFalse(output.exists())
            context.close.assert_called_once()

    def test_unrelated_page_failure_is_not_silently_swallowed(self):
        from playwright.sync_api import Error as PlaywrightError
        spec = importlib.util.spec_from_file_location("unrelated_record_recipe", ROOT / "scripts/record_recipe.py")
        recorder = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(recorder)
        page = Mock()
        page.is_closed.return_value = False
        page.wait_for_timeout.side_effect = PlaywrightError("Synthetic unrelated browser failure")
        context = Mock()
        context.pages = [page]
        context.new_page.return_value = page
        browser = Mock()
        browser.new_context.return_value = context
        runtime = SimpleNamespace(chromium=SimpleNamespace(launch=lambda **kw: browser))
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "recipe.json"
            with patch.object(recorder, "sync_playwright", lambda: contextlib.nullcontext(runtime)), patch("sys.argv", ["record_recipe.py", "--url", "http://127.0.0.1/report", "--output", str(output)]):
                with self.assertRaisesRegex(RuntimeError, "RECORDER_BROWSER_FAILED"):
                    recorder.main()
            self.assertFalse(output.exists())


    def test_cancelled_search_requests_fail_closed_without_breaking_recording_dispatch(self):
        """Aborted requests during a loading transition cannot crash the recorder's route callback."""
        from playwright.sync_api import Error as PlaywrightError
        spec = importlib.util.spec_from_file_location("request_record_recipe", ROOT / "scripts/record_recipe.py")
        recorder = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(recorder)
        stop = Event()
        stop.set()
        page = Mock()
        context = Mock()
        context.new_page.return_value = page
        handlers = []
        context.route.side_effect = lambda pattern, handler: handlers.append(handler)
        browser = Mock()
        browser.new_context.return_value = context
        runtime = SimpleNamespace(chromium=SimpleNamespace(launch=lambda **kw: browser))
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "recipe.json"
            with patch.object(recorder, "sync_playwright", lambda: contextlib.nullcontext(runtime)), patch("sys.argv", ["record_recipe.py", "--url", "http://127.0.0.1/report", "--output", str(output)]):
                with self.assertRaisesRegex(RuntimeError, "RECORDER_CANCELLED"):
                    recorder.main(stop_event=stop)
        self.assertEqual(len(handlers), 1)
        request = Mock()
        request.request.url = "http://127.0.0.1/api/search"
        request.fetch.side_effect = PlaywrightError("net::ERR_ABORTED")
        handlers[0](request)
        request.fetch.assert_called_once_with(max_redirects=0)
        request.abort.assert_called_once()
        self.assertFalse(request.fulfill.called)

        request = Mock()
        request.request.url = "http://127.0.0.1/api/search"
        request.fetch.return_value = SimpleNamespace(status=200)
        request.fulfill.side_effect = PlaywrightError("Route already handled during navigation")
        handlers[0](request)
        request.abort.assert_called_once()

        request = Mock()
        request.request.url = "https://external.invalid/resource"
        handlers[0](request)
        request.abort.assert_called_once()
        self.assertFalse(request.fetch.called)
