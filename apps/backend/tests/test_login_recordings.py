import unittest
import os
from app.services.login_recordings import LoginRecordings

class LoginRecordingTests(unittest.TestCase):
    def test_access_is_owner_bound_and_revoked_session_cancels(self):
        valid = {"owner-a", "owner-b"}
        manager = LoginRecordings(session_valid=lambda owner: owner in valid)
        entry = manager._new_entry("owner-a", 1, 1)
        manager._entries[entry["id"]] = entry
        self.assertEqual(manager.get(entry["id"], "owner-a")["status"], "RECORDING")
        with self.assertRaisesRegex(RuntimeError, "LOGIN_RECORDING_NOT_FOUND"):
            manager.get(entry["id"], "owner-b")
        valid.remove("owner-a"); manager.sweep()
        self.assertEqual(entry["status"], "CANCELLED")
    def test_corporate_target_selection_uses_owned_process_and_metadata_only(self):
        import io
        import json
        from unittest.mock import Mock
        messages = [{"type": "target", "field": field, "target": {"selector": selector, "frames": []}}
            for field, selector in (("username_target", "#user"), ("password_target", "#pass"), ("submit_target", "#submit"))]
        messages.append({"type": "done"})
        process = Mock(stdin=io.StringIO(), stdout=io.StringIO("".join(json.dumps(item) + "\n" for item in messages)))
        process.poll.return_value = 0
        manager = LoginRecordings(session_valid=lambda owner: True, start_process=lambda: process)
        result = manager.start("owner", 1, 1, {"login_url": "https://indicadoresenergisaess.scl.corp/sgind/"})
        manager._entries[result["id"]]["thread"].join(timeout=2)
        result = manager.get(result["id"], "owner")
        self.assertEqual(result["status"], "DONE")
        self.assertEqual(result["targets"]["password_target"], {"selector": "#pass", "frames": []})
        self.assertEqual(set(result["targets"]), {"username_target", "password_target", "submit_target"})
        self.assertNotIn("owner", result)
        manager.close_all()

    @unittest.skipUnless(os.getenv("NEXER_RUN_LOGIN_PROFILE_E2E") == "1", "Synthetic Edge picker process opt-in")
    def test_owned_process_delivers_targets_and_exits_without_data_values(self):
        import json
        import subprocess
        import sys
        import threading
        import time
        from pathlib import Path
        from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
        submitted = []
        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args): pass
            def do_GET(self):
                self.send_response(200); self.send_header("Content-Type", "text/html"); self.end_headers()
                self.wfile.write(b'<form method="post"><input id="user" value="user-private-canary"><input id="pass" type="password" value="password-private-canary"><button id="submit">Enter</button></form>')
            def do_POST(self):
                submitted.append(True); self.send_response(400); self.end_headers()
        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
        processes = []
        def start_process():
            process = subprocess.Popen([sys.executable, str(Path(__file__).with_name("login_picker_process_fixture.py"))], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, encoding="utf-8", creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
            processes.append(process); return process
        manager = LoginRecordings(session_valid=lambda owner: True, start_process=start_process)
        try:
            result = manager.start("owner", 1, 1, {"login_url": f"http://127.0.0.1:{server.server_port}/login"})
            deadline = time.monotonic() + 20
            while result["status"] == "RECORDING" and time.monotonic() < deadline:
                time.sleep(0.1); result = manager.get(result["id"], "owner")
            self.assertEqual(result["status"], "DONE")
            self.assertEqual(set(result["targets"]), {"username_target", "password_target", "submit_target"})
            self.assertNotIn("private-canary", json.dumps(result))
            self.assertEqual(submitted, [])
            manager.close_all()
            self.assertIsNotNone(processes[0].poll())
        finally:
            manager.close_all(); server.shutdown(); server.server_close(); thread.join(timeout=5)
