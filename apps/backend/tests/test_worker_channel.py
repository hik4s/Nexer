import unittest
from types import SimpleNamespace

class WorkerChannelTests(unittest.TestCase):
    def setUp(self):
        from app.worker_channel import WorkerCredentialChannel
        from app.ephemeral_credentials import EphemeralCredentialVault
        self.vault = EphemeralCredentialVault()
        self.execution = SimpleNamespace(status="RUNNING", worker_id="worker-incarnation", cancel_requested=False)
        self.active = True
        self.channel = WorkerCredentialChannel(
            vault=self.vault, lookup_execution=lambda execution_id: self.execution if execution_id == 1 else None,
            session_valid=lambda owner: self.active)
        self.channel.configure("worker-incarnation", "synthetic-capability")
        self.channel.bind(1, "owner-session")
        self.vault.put(1, "owner-session", {"SGIND": {"username": "canary-user", "password": "canary-secret"}}, ttl_seconds=60)

    def test_only_bound_execution_and_system_are_available(self):
        self.assertEqual(self.channel.resolve(1, "SGIND", "synthetic-capability")["password"], "canary-secret")
        for execution, system, token in [(2, "SGIND", "synthetic-capability"), (1, "IQOS", "synthetic-capability"), (1, "SGIND", "wrong")]:
            with self.assertRaisesRegex(RuntimeError, "^CREDENTIALS_UNAVAILABLE$"):
                self.channel.resolve(execution, system, token)

    def test_claim_cancellation_session_and_terminal_status_fail_closed(self):
        for attribute, value in [("worker_id", "foreign-worker"), ("cancel_requested", True), ("status", "SUCCEEDED")]:
            old = getattr(self.execution, attribute)
            setattr(self.execution, attribute, value)
            with self.assertRaises(RuntimeError):
                self.channel.resolve(1, "SGIND", "synthetic-capability")
            setattr(self.execution, attribute, old)
        self.active = False
        with self.assertRaises(RuntimeError):
            self.channel.resolve(1, "SGIND", "synthetic-capability")

    def test_restart_and_release_revoke_credentials(self):
        self.channel.configure("next-incarnation", "next-capability")
        with self.assertRaises(RuntimeError):
            self.channel.resolve(1, "SGIND", "synthetic-capability")
        with self.assertRaises(RuntimeError):
            self.vault.get(1, "owner-session", "SGIND")

    def test_no_secret_in_repr_or_errors(self):
        self.assertNotIn("synthetic-capability", repr(self.channel))
        self.assertNotIn("canary", repr(self.channel))
