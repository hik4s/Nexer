import unittest
from fastapi.testclient import TestClient
from app.main import app

class LocalPairingTests(unittest.TestCase):
    def setUp(self):
        from app.local_pairing import PairingAuthority
        self.now = 100.0
        self.authority = PairingAuthority(clock=lambda: self.now)

    def test_code_is_single_use_and_repr_is_safe(self):
        code = self.authority.issue()
        self.assertNotIn(code, repr(self.authority))
        self.assertTrue(self.authority.consume(code))
        self.assertFalse(self.authority.consume(code))

    def test_expiration_at_boundary(self):
        code = self.authority.issue()
        self.now = 400
        self.assertFalse(self.authority.consume(code))

    def test_five_invalid_attempts_revoke_code(self):
        code = self.authority.issue()
        for _ in range(5):
            self.assertFalse(self.authority.consume("incorrect"))
        self.assertFalse(self.authority.consume(code))

    def test_reissue_invalidates_previous_code(self):
        old = self.authority.issue()
        new = self.authority.issue()
        self.assertFalse(self.authority.consume(old))
        self.assertTrue(self.authority.consume(new))

class PairingApiTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app, base_url="http://127.0.0.1:8000",
            client=("127.0.0.1", 50000), headers={"Origin": "http://127.0.0.1:5173"})
        from app.local_pairing import pairing_authority
        self.code = pairing_authority.issue()

    def test_login_cookie_logout_and_no_code_echo(self):
        rejected = self.client.post("/auth/login", json={"pairing_code": "incorrect"})
        self.assertEqual(rejected.status_code, 401)
        accepted = self.client.post("/auth/login", json={"pairing_code": self.code})
        self.assertEqual(accepted.status_code, 200)
        self.assertNotIn(self.code, accepted.text)
        cookie = accepted.headers["set-cookie"].lower()
        self.assertIn("httponly", cookie)
        self.assertIn("samesite=strict", cookie)
        self.assertTrue(self.client.get("/auth/session").json()["authenticated"])
        self.assertEqual(self.client.post("/auth/login", json={"pairing_code": self.code}).status_code, 401)
        self.client.post("/auth/logout")
        self.assertFalse(self.client.get("/auth/session").json()["authenticated"])

    def test_no_environment_test_bypass(self):
        self.assertEqual(self.client.get("/secure-probe").status_code, 401)

    def test_origin_host_and_peer_are_restricted(self):
        for headers in [{"Origin": "https://evil.example"}, {"Host": "evil.example"}]:
            self.assertEqual(self.client.post("/auth/login", json={"pairing_code": self.code}, headers=headers).status_code, 403)
        external = TestClient(app, base_url="http://127.0.0.1:8000", client=("192.0.2.1", 50000))
        self.assertEqual(external.get("/health").status_code, 403)

    def test_logout_revokes_execution_credentials(self):
        from app.security import credential_vault, SESSION_COOKIE_NAME
        self.client.post("/auth/login", json={"pairing_code": self.code})
        token = self.client.cookies.get(SESSION_COOKIE_NAME)
        credential_vault.put(1, token, {"SGIND": {"username": "canary-user", "password": "canary-secret"}}, ttl_seconds=60)
        self.client.post("/auth/logout")
        with self.assertRaisesRegex(RuntimeError, "^CREDENTIALS_UNAVAILABLE$"):
            credential_vault.get(1, token, "SGIND")

    def test_missing_origin_is_rejected(self):
        client = TestClient(app, base_url="http://127.0.0.1:8000", client=("127.0.0.1", 50000))
        self.assertEqual(client.post("/auth/login", json={"pairing_code": self.code}).status_code, 403)

    def test_old_credentials_do_not_create_session(self):
        response = self.client.post("/auth/login", json={"username": "old", "password": "synthetic"})
        self.assertEqual(response.status_code, 422)
        self.assertNotIn("synthetic", response.text)
