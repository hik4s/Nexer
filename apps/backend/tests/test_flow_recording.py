import json
import os
from pathlib import Path
import subprocess
import sys
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from app.services.flow_recordings import FlowRecordings

class FlowRecordingTests(unittest.TestCase):
    def test_https_safe_route_is_sent_before_launch_and_prepares(self):
        import io
        from unittest.mock import Mock
        process = Mock(stdin=io.StringIO(), stdout=io.StringIO(''))
        process.poll.return_value = 0
        process.stdin.close = lambda: None
        manager = FlowRecordings(session_valid=lambda owner: True, start_process=lambda: process)
        url = "https://example.invalid/sgind/#/relatatendtodasocorrencias"
        result = manager.start_flow("owner", url)
        self.assertEqual(result["phase"], "PREPARING")
        self.assertEqual(json.loads(process.stdin.getvalue().splitlines()[0])["login_url"], url)

    def test_invalid_urls_rejected_before_launch(self):
        called = []
        manager = FlowRecordings(session_valid=lambda owner: True, start_process=lambda: called.append(True))
        for url in ("http://example.invalid/", "https://user:pass@example.invalid/", "https://example.invalid/?secret=x", "https://example.invalid/#token=x"):
            with self.subTest(url=url), self.assertRaises((RuntimeError, ValueError)):
                manager.start_flow("owner", url)
        self.assertEqual(called, [])

    def test_preparing_cannot_finish_or_publish_preparation_only_recipe(self):
        import io
        from unittest.mock import Mock
        manager = FlowRecordings(session_valid=lambda owner: True)
        entry = manager._new_entry("owner", 0, 1)
        entry["phase"] = "PREPARING"
        entry["process"] = Mock(stdin=io.StringIO(), stdout=io.StringIO(json.dumps({"type": "done", "recipe": {}}) + "\n"))
        manager._entries[entry["id"]] = entry
        with self.assertRaisesRegex(RuntimeError, "PREPARING"):
            manager.finish(entry["id"], "owner")
        manager._read(entry)
        self.assertEqual(entry["status"], "FAILED")
        self.assertIsNone(entry["recipe"])

    def test_started_protocol_progress_allows_parameterized_recipe(self):
        import io
        from unittest.mock import Mock
        recipe = {
            "schema_version": 1,
            "name": "Report",
            "variables": {"base_url": {"type": "string", "required": True}, "company": {"type": "string", "required": True}},
            "steps": [
                {"id": "open", "action": "navigate", "url": "{{base_url}}"},
                {"id": "company", "action": "fill", "selector": "input", "value": "{{company}}"},
            ],
            "output": {"type": "file"},
        }
        manager = FlowRecordings(session_valid=lambda owner: True)
        entry = manager._new_entry("owner", 0, 1)
        entry["phase"] = "PREPARING"
        messages = [{"type": "started"}, {"type": "done", "recipe": recipe}]
        entry["process"] = Mock(stdin=io.StringIO(), stdout=io.StringIO(''.join(json.dumps(message) + "\n" for message in messages)))
        manager._read(entry)
        self.assertEqual(entry["phase"], "RECORDING")
        self.assertEqual(entry["status"], "DONE")
        self.assertEqual(entry["recipe"], recipe)

    def test_cancel_preparation_and_eof_leave_no_recipe(self):
        import io
        from unittest.mock import Mock
        manager = FlowRecordings(session_valid=lambda owner: True)
        entry = manager._new_entry("owner", 0, 1)
        entry["phase"] = "PREPARING"
        entry["process"] = Mock(stdin=io.StringIO(), stdout=io.StringIO(''))
        manager._entries[entry["id"]] = entry
        result = manager.cancel(entry["id"], "owner")
        manager._read(entry)
        self.assertEqual(result["status"], "CANCELLED")
        self.assertEqual(entry["status"], "CANCELLED")
        self.assertIsNone(entry["recipe"])

    @unittest.skipUnless(os.getenv("NEXER_RUN_RECORDER_E2E") == "1", "Local Edge recorder process opt-in")
    def test_private_process_records_locations_without_entered_values(self):
        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args): pass
            def do_GET(self):
                self.send_response(200); self.send_header("Content-Type", "text/html"); self.end_headers()
                self.wfile.write(b'<input id="company"><button id="button" type="button">Continue</button>')
        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
        processes = []
        def start():
            process = subprocess.Popen([sys.executable, str(Path(__file__).with_name("flow_recording_process_fixture.py"))], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, encoding="utf-8", creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
            processes.append(process); return process
        manager = FlowRecordings(session_valid=lambda owner: owner == "owner", start_process=start)
        try:
            result = manager.start_flow("owner", f"http://127.0.0.1:{server.server_port}/")
            deadline = time.monotonic() + 20
            while time.monotonic() < deadline:
                result = manager.get(result["id"], "owner")
                if result["status"] != "RECORDING": break
                time.sleep(.1)
            self.assertEqual(result["status"], "DONE", result)
            self.assertNotIn("recorded-value-canary", json.dumps(result))
            self.assertTrue(any(step["action"] == "fill" for step in result["recipe"]["steps"]))
            with self.assertRaises(RuntimeError): manager.get(result["id"], "other-owner")
            processes[0].wait(timeout=10)
        finally:
            manager.close_all(); server.shutdown(); server.server_close(); thread.join(timeout=5)
