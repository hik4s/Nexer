import unittest
from types import SimpleNamespace
from app.ephemeral_credentials import EphemeralCredentialVault
from app.worker_channel import WorkerCredentialChannel


class WorkerChannelCleanupTests(unittest.TestCase):
    def setUp(self):
        self.now = 0
        self.active = True
        self.execution = SimpleNamespace(status="QUEUED", worker_id=None, cancel_requested=False)
        self.vault = EphemeralCredentialVault(clock=lambda: self.now)
        self.channel = WorkerCredentialChannel(
            vault=self.vault, lookup_execution=lambda _: self.execution,
            session_valid=lambda _: self.active)
        self.channel.configure("worker", "synthetic-capability")
        self.vault.put(1, "synthetic-owner", {"SGIND": {
            "username": "canary-user", "password": "canary-password"}}, ttl_seconds=60)
        self.channel.bind(1, "synthetic-owner")

    def test_queued_binding_survives_cleanup(self):
        self.assertEqual(self.channel.sweep(), 0)
        with self.assertRaisesRegex(RuntimeError, "CREDENTIALS_ALREADY_BOUND"):
            self.channel.bind(1, "another-owner")
        self.assertEqual(self.vault.get(1, "synthetic-owner", "SGIND")["username"], "canary-user")

    def assert_removed(self):
        self.assertEqual(self.channel.sweep(), 1)
        self.assertEqual(self.channel.sweep(), 0)
        with self.assertRaisesRegex(RuntimeError, "CREDENTIALS_UNAVAILABLE"):
            self.vault.get(1, "synthetic-owner", "SGIND")
        self.channel.bind(1, "new-owner")

    def test_expired_credentials_remove_binding(self):
        self.now = 60
        self.assert_removed()

    def test_logout_removes_binding(self):
        self.active = False
        self.assert_removed()

    def test_terminal_execution_removes_binding(self):
        for status in ("SUCCEEDED", "FAILED", "CANCELLED", "PARTIAL"):
            with self.subTest(status=status):
                self.setUp()
                self.execution.status = status
                self.assert_removed()

    def test_cancelled_execution_removes_binding(self):
        self.execution.cancel_requested = True
        self.assert_removed()

    def test_uncommitted_execution_keeps_binding_until_expiry(self):
        self.execution = None
        self.assertEqual(self.channel.sweep(), 0)
        self.assertEqual(self.vault.get(1, "synthetic-owner", "SGIND")["username"], "canary-user")
        self.now = 60
        self.assert_removed()

    def test_foreign_worker_removes_binding(self):
        self.execution.status = "RUNNING"
        self.execution.worker_id = "foreign-worker"
        self.assert_removed()
