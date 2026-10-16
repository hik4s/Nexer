"""Eye Developer uses authenticated, non-persisting local inspection."""
import json
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest.mock import patch
from test_client import AuthenticatedTestClient
from app.main import app
from app.services.developer_eye import probe


class DeveloperEyeApiTests(unittest.TestCase):
    def test_authenticated_probe_strict_request_and_safe_response(self):
        client=AuthenticatedTestClient(app)
        expected={"mode":"headless","status":"FOUND","matches":1,"visible":True,"enabled":True,"elapsed_ms":123}
        with patch("app.api.developer_eye.probe",return_value=expected) as mocked:
            response=client.post("/developer-eye/probe",json={"url":"https://example.test/","selector":"#search"})
            self.assertEqual(response.status_code,200)
            self.assertEqual(response.json(),expected)
            self.assertEqual(response.headers.get("Cache-Control"),"no-store")
            mocked.assert_called_once()
            self.assertEqual(client.post("/developer-eye/probe",json={"url":"https://example.test/",
                "selector":"#search","script":"private-canary"}).status_code,422)
            client.cookies.clear()
            self.assertEqual(client.post("/developer-eye/probe",json={"url":"https://example.test/","selector":"#x"}).status_code,401)
            self.assertNotIn("private-canary",json.dumps(response.json()))


class DeveloperEyeHeadlessTests(unittest.TestCase):
    def test_headless_probe_returns_only_structural_selector_facts(self):
        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                html=b'<html><body><button id="search">private-canary</button><div class="many"></div><div class="many"></div><input type=password value=hidden-secret></body></html>'
                self.send_response(200)
                self.send_header("Content-Type","text/html; charset=UTF-8")
                self.end_headers()
                self.wfile.write(html)
            def log_message(self,*args): pass

        server=ThreadingHTTPServer(("127.0.0.1",0),Handler)
        thread=threading.Thread(target=server.serve_forever,daemon=True)
        thread.start()
        try:
            url=f"http://127.0.0.1:{server.server_port}/"
            found=probe(url,"#search")
            self.assertEqual(found["status"],"FOUND")
            self.assertEqual(found["matches"],1)
            self.assertTrue(found["visible"])
            self.assertNotIn("private-canary",json.dumps(found))
            self.assertNotIn("hidden-secret",json.dumps(found))
            self.assertNotIn(url,json.dumps(found))
            multiple=probe(url,".many")
            self.assertEqual(multiple["status"],"AMBIGUOUS")
            self.assertEqual(multiple["matches"],2)
        finally:
            server.shutdown();server.server_close();thread.join(timeout=5)

    def test_invalid_urls_rejected_before_browser_start(self):
        with self.assertRaises(ValueError):
            probe("file:///etc/passwd","#search")
        with self.assertRaises(ValueError):
            probe("https://example.test/?token=private","#search")
