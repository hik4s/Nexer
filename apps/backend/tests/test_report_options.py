import copy
import json
import os
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import unittest
from unittest.mock import Mock

from app.services.report_options import ReportOptionsError, read_options


class ReportOptionsTests(unittest.TestCase):
    def test_remote_and_credential_urls_are_rejected_before_browser_creation(self):
        recipe = {"schema_version": 1, "name": "Options", "variables": {"base_url": {"type": "string"}},
                  "steps": [{"id": "open", "action": "navigate", "url": "{{base_url}}"}], "output": {"type": "file"}}
        factory = Mock()
        for url in ("https://corporate.invalid/report", "http://user:password@127.0.0.1/report", "http://127.0.0.1/report?token=canary"):
            with self.subTest(url=url), self.assertRaises(ReportOptionsError):
                read_options(recipe, {"base_url": url}, playwright_factory=factory)
        factory.assert_not_called()

    def test_browser_failures_never_return_underlying_data(self):
        recipe = {"schema_version": 1, "name": "Options", "variables": {},
                  "steps": [{"id": "open", "action": "navigate", "url": "http://127.0.0.1/form"}], "output": {"type": "file"}}
        with self.assertRaisesRegex(ReportOptionsError, "^OPTIONS_PAGE_UNAVAILABLE$"):
            read_options(recipe, {}, playwright_factory=Mock(side_effect=RuntimeError("synthetic-private-canary")))


@unittest.skipUnless(os.getenv("NEXER_RUN_REPORT_OPTIONS_E2E") == "1", "Set NEXER_RUN_REPORT_OPTIONS_E2E=1 for synthetic Edge option catalogs")
class ReportOptionsEdgeTests(unittest.TestCase):
    def test_catalog_uses_current_site_and_filters_without_persisting_values(self):
        html = b"""<select id=company onchange="setTimeout(() => document.querySelector('#regional').innerHTML=this.value==='b'?'<option value=south>South live</option>':'<option value=north>North live</option>', 1600)">
            <option value=a selected>Company A live</option><option value=b>Company B live</option></select>
            <select id=regional><option value=north selected>North live</option></select>"""
        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                self.send_response(200); self.send_header("Content-Type", "text/html"); self.end_headers()
                if self.path == "/framed":
                    self.wfile.write(b'<iframe src="/field"></iframe>')
                elif self.path == "/field":
                    self.wfile.write(b"""<select id=regional><option value=old>Old</option></select><script>setTimeout("document.querySelector('#regional').innerHTML='<option value=new>New live</option>'",1600)</script>""")
                else:
                    self.wfile.write(html.replace(b"1600", b"5000") if self.path == "/slow" else html)
            def log_message(self, *args):
                pass
        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
        recipe = {"schema_version": 1, "name": "Options", "variables": {
            "base_url": {"type": "string"}, "company": {"type": "string", "field": {"control": "select"}}, "regional": {"type": "string", "field": {"control": "select"}}},
            "steps": [{"id": "open", "action": "navigate", "url": "{{base_url}}"},
                      {"id": "company", "action": "select", "selector": "#company", "value": "{{company}}"},
                      {"id": "regional", "action": "select", "selector": "#regional", "value": "{{regional}}"}], "output": {"type": "file"}}
        original = copy.deepcopy(recipe)
        try:
            url = f"http://127.0.0.1:{server.server_port}/form"
            from browser_manager import BrowserManager
            def page_factory():
                return BrowserManager(headless=True).create_monitored_login_page({"login_url": url, "allowed_origins": [url.rsplit("/", 1)[0]]}, authorize=lambda: None)
            protected = read_options(recipe, {"base_url": url}, page_factory=page_factory)
            self.assertEqual([item["value"] for item in protected["fields"]["company"]["options"]], ["a", "b"])
            initial = read_options(recipe, {"base_url": url})
            self.assertEqual([item["value"] for item in initial["fields"]["company"]["options"]], ["a", "b"])
            filtered = read_options(recipe, {"base_url": url, "company": "b", "regional": "north"})
            self.assertEqual(filtered["fields"]["regional"]["options"], [{"value": "south", "label": "South live", "disabled": False}])
            with self.assertRaises(ReportOptionsError):
                read_options(recipe, {"base_url": url.replace("/form", "/slow"), "company": "b"})
            self.assertNotIn("selected", json.dumps(filtered))
            framed = copy.deepcopy(recipe)
            framed["steps"] = [framed["steps"][0], {**framed["steps"][-1], "frames": ["iframe"]}]
            framed_result = read_options(framed, {"base_url": url.replace("/form", "/framed")})
            self.assertEqual(framed_result["fields"]["regional"]["options"], [{"value": "new", "label": "New live", "disabled": False}])
            self.assertEqual(recipe, original)
            self.assertNotIn("Company A live", json.dumps(recipe))
        finally:
            server.shutdown(); server.server_close(); thread.join(timeout=5)
