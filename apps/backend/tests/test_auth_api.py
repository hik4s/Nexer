import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.config import Settings
from app.main import app
from app.security import (
    authenticate,
    hash_password,
    is_auth_configured,
    verify_password,
)


class AuthenticationTests(unittest.TestCase):
    def test_password_hash_verifies_without_storing_plaintext(self):
        encoded = hash_password("uma-senha-local-segura")
        self.assertNotIn("uma-senha-local-segura", encoded)
        self.assertTrue(verify_password("uma-senha-local-segura", encoded))
        self.assertFalse(verify_password("senha-errada", encoded))

    def test_malformed_hash_fails_closed(self):
        self.assertFalse(is_auth_configured("operator", "not-a-hash"))
        self.assertFalse(verify_password("anything", "pbkdf2_sha256$1$x$y"))

    def test_credentials_are_checked_server_side(self):
        encoded = hash_password("uma-senha-local-segura")
        self.assertTrue(authenticate("operator", "uma-senha-local-segura", "operator", encoded))
        self.assertFalse(authenticate("operator", "errada", "operator", encoded))
        self.assertFalse(authenticate("intruso", "uma-senha-local-segura", "operator", encoded))
