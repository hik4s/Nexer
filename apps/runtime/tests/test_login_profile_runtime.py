import os
import unittest
from unittest.mock import Mock
from types import SimpleNamespace
from login_profiles import LoginBrowserPolicy, profile_key, authenticate_profile

class ProfileRuntimeTests(unittest.TestCase):
    def test_recipe_rejects_mixed_login_contracts_before_publication(self):
        from recipe import validate_recipe, RecipeValidationError
        recipe = {"schema_version": 1, "name": "Mixed login", "login_profile": {"id": 1, "version": 1}, "authentication": {"login_selectors": ["#login"]}, "variables": {}, "steps": [{"id": "open", "action": "navigate", "url": "https://site.invalid"}], "output": {"type": "file"}}
        with self.assertRaises(RecipeValidationError): validate_recipe(recipe)
    def test_marker_already_visible_does_not_prove_login(self):
        locator = Mock()
        locator.count.return_value = 1
        locator.is_visible.return_value = True
        locator.get_attribute.return_value = "password"
        page = Mock()
        page.locator.return_value = locator
        configuration = {"login_url": "https://site.invalid/login", "username_target": {"selector": "#user"}, "password_target": {"selector": "#pass"}, "submit_target": {"selector": "#submit"}, "success_rule": {"kind": "marker", "target": {"selector": "#logo"}}}
        with self.assertRaisesRegex(RuntimeError, "^LOGIN_FAILED$"):
            authenticate_profile(page, configuration, {"username": "synthetic", "password": "canary"}, cancellation_requested=lambda: False)
        locator.fill.assert_not_called()
    def test_allowed_origins_cannot_include_corporate_or_untrusted_destination(self):
        policy = LoginBrowserPolicy({"login_url": "https://site.invalid/login", "allowed_origins": ["https://site.invalid"]}, authorize=lambda: None)
        policy.validate_url("https://site.invalid/home")
        for url in ("https://other.invalid", "https://site.invalid.evil", "https://user:secret@site.invalid", "https://indicadoresenergisaess.scl.corp/sgind"):
            with self.subTest(url=url), self.assertRaises(RuntimeError): policy.validate_url(url)
        self.assertEqual(profile_key(4, 2), "profile-4-v2")
    def test_login_failures_never_expose_credential_values(self):
        page = SimpleNamespace(corporate_policy=SimpleNamespace(check=lambda: None), goto=lambda *args, **kwargs: (_ for _ in ()).throw(ValueError("private-password-canary")))
        with self.assertRaisesRegex(RuntimeError, "^LOGIN_FAILED$"):
            authenticate_profile(page, {"login_url": "https://site.invalid/login"}, {"username": "synthetic", "password": "private-password-canary"}, cancellation_requested=lambda: False)


@unittest.skipUnless(os.getenv("NEXER_RUN_LOGIN_PROFILE_E2E") == "1", "Synthetic profile login Edge opt-in")
class ProfileLoginEdgeTests(unittest.TestCase):
    def test_ephemeral_login_succeeds_only_with_explicit_rule(self):
        import threading
        from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
        from urllib.parse import parse_qs
        from browser_manager import BrowserManager
        from login_profiles import LoginExecutionGuard
        received = []
        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args): pass
            def do_GET(self):
                self.send_response(200); self.send_header("Content-Type", "text/html"); self.end_headers()
                if self.path == "/login":
                    self.wfile.write(b'<form action="/login" method="post"><input id="user" name="user"><input id="pass" name="pass" type="password"><button id="submit">Enter</button></form>')
                elif self.headers.get("Cookie") == "session=synthetic":
                    self.wfile.write(b'<h1 id="home">Home</h1><input id="company">')
                else: self.wfile.write(b'<input id="pass" type="password">')
            def do_POST(self):
                body = parse_qs(self.rfile.read(int(self.headers.get("Content-Length", 0))).decode())
                received.append(body == {"user": ["user-canary"], "pass": ["password-canary"]})
                self.send_response(303); self.send_header("Location", "/home"); self.send_header("Set-Cookie", "session=synthetic; HttpOnly; SameSite=Strict"); self.end_headers()
        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
        origin = f"http://127.0.0.1:{server.server_port}"
        configuration = {"login_url": origin + "/login", "allowed_origins": [origin], "username_target": {"selector": "#user", "frames": []}, "password_target": {"selector": "#pass", "frames": []}, "submit_target": {"selector": "#submit", "frames": []}, "success_rule": {"kind": "marker", "target": {"selector": "#home", "frames": []}}}
        manager = BrowserManager(headless=True)
        page = None
        try:
            page = manager.create_monitored_login_page(configuration, authorize=lambda: None)
            authenticate_profile(page, configuration, {"username": "user-canary", "password": "password-canary"}, cancellation_requested=lambda: False)
            self.assertEqual(received, [True])
            LoginExecutionGuard(configuration).ensure_authenticated(page)
            self.assertTrue(page.locator("#home").is_visible())
        finally:
            if page: page.close()
            server.shutdown(); server.server_close(); thread.join(timeout=5)
