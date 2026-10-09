import json
import os
import subprocess
import sys
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

class CredentialTransportTests(unittest.TestCase):
    def test_worker_process_receives_credentials_only_with_capability(self):
        from nexer_worker.credential_client import ExecutionCredentialClient
        secret = {"username": "canary-user", "password": "canary-secret"}
        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                accepted = self.headers.get("x-nexer-worker") == "synthetic-capability" and self.path == "/internal/credentials/1/SGIND"
                self.send_response(200 if accepted else 401)
                self.end_headers()
                self.wfile.write(json.dumps(secret if accepted else {"error": "unavailable"}).encode())
            def log_message(self, *args):
                pass
        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        url = "http://127.0.0.1:" + str(server.server_port)
        script = (
            "import sys,json; from nexer_worker.credential_client import ExecutionCredentialClient; "
            "config=json.loads(sys.stdin.readline()); "
            "client=ExecutionCredentialClient(config['url'],config['capability']); "
            "value=client.resolve(1,'SGIND'); "
            "assert value == {'username':'canary-user','password':'canary-secret'}; "
            "print('EXCHANGE_OK')"
        )
        try:
            result = subprocess.run([sys.executable, "-c", script], input=json.dumps({
                "url": url, "capability": "synthetic-capability"}) + "\n",
                text=True, capture_output=True, timeout=10, env=os.environ.copy())
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout.strip(), "EXCHANGE_OK")
            self.assertNotIn("canary", result.stdout)
            with self.assertRaisesRegex(RuntimeError, "^CREDENTIALS_UNAVAILABLE$"):
                ExecutionCredentialClient(url, "wrong").resolve(1, "SGIND")
            with self.assertRaises(RuntimeError):
                ExecutionCredentialClient(url, "synthetic-capability").resolve(2, "SGIND")
            self.assertNotIn("synthetic-capability", repr(ExecutionCredentialClient(url, "synthetic-capability")))
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)

    def test_non_local_destination_is_rejected(self):
        from nexer_worker.credential_client import ExecutionCredentialClient
        for url in ["https://evil.example", "http://user:pass@127.0.0.1:8000", "http://127.0.0.1:8000/path"]:
            with self.assertRaises(ValueError):
                ExecutionCredentialClient(url, "synthetic")
