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
    def test_remote_recording_rejected_before_launch(self):
        called = []
        manager = FlowRecordings(session_valid=lambda owner: True, start_process=lambda: called.append(True))
        with self.assertRaisesRegex(RuntimeError, "LOCAL_ONLY"): manager.start_flow("owner", "https://example.invalid")
        self.assertEqual(called, [])
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
