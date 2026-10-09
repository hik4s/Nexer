import unittest
from types import SimpleNamespace
from unittest.mock import patch
from fastapi.testclient import TestClient
from app.main import app
from app.security import credential_vault, issue_session, revoke_session
from app.worker_channel import worker_channel

class InternalCredentialRouteTests(unittest.TestCase):
    def setUp(self):
        worker_channel.configure("test-incarnation", "synthetic-capability")
        self.token = issue_session("local", 600)
        worker_channel.bind(1, self.token)
        credential_vault.put(1, self.token, {"SGIND": {"username": "canary-user", "password": "canary-secret"}}, ttl_seconds=60)
        self.execution = SimpleNamespace(worker_id="test-incarnation", status="RUNNING", cancel_requested=False)
        self.client = TestClient(app, base_url="http://127.0.0.1:8000", client=("127.0.0.1", 50000),
            headers={"Origin": "http://127.0.0.1:5173", "x-nexer-worker": "synthetic-capability"})
        self.lookup = patch.object(worker_channel, "_lookup", return_value=self.execution)
        self.lookup.start()

    def tearDown(self):
        self.lookup.stop()
        worker_channel.revoke(1)
        revoke_session(self.token)

    def test_authenticated_worker_route_and_release(self):
        response = self.client.get("/internal/credentials/1/SGIND")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers.get("cache-control"), "no-store")
        self.assertEqual(response.json()["password"], "canary-secret")
        self.execution.status = "SUCCEEDED"
        self.assertEqual(self.client.post("/internal/credentials/1/release").status_code, 200)
        with self.assertRaises(RuntimeError):
            credential_vault.get(1, self.token, "SGIND")

    def test_wrong_capability_and_revoked_session_expose_no_credentials(self):
        rejected = self.client.get("/internal/credentials/1/SGIND", headers={"x-nexer-worker": "wrong"})
        self.assertEqual(rejected.status_code, 401)
        self.assertNotIn("canary", rejected.text)
        revoke_session(self.token)
        rejected = self.client.get("/internal/credentials/1/SGIND")
        self.assertEqual(rejected.status_code, 401)
        self.assertNotIn("canary", rejected.text)
