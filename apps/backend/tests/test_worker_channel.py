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


class ParallelWorkerChannelTests(unittest.TestCase):
    def test_capabilities_and_bindings_are_isolated_per_worker(self):
        from app.worker_channel import WorkerCredentialChannel
        from app.ephemeral_credentials import EphemeralCredentialVault
        vault = EphemeralCredentialVault()
        executions = {1: SimpleNamespace(status="RUNNING", worker_id="a", cancel_requested=False), 2: SimpleNamespace(status="RUNNING", worker_id="b", cancel_requested=False)}
        channel = WorkerCredentialChannel(vault=vault, lookup_execution=executions.get, session_valid=lambda owner: True)
        channel.configure("a", "cap-a"); channel.register("b", "cap-b")
        for execution_id, worker in ((1, "a"), (2, "b")):
            channel.bind(execution_id, "owner", expected_worker_id=worker)
            vault.put(execution_id, "owner", {"profile-1-v1": {"username": worker, "password": "synthetic-" + worker}}, ttl_seconds=60)
        self.assertEqual(channel.resolve(1, "profile-1-v1", "cap-a")["username"], "a")
        self.assertEqual(channel.resolve(2, "profile-1-v1", "cap-b")["username"], "b")
        with self.assertRaises(RuntimeError): channel.resolve(1, "profile-1-v1", "cap-b")
        channel.unregister("a")
        self.assertEqual(channel.resolve(2, "profile-1-v1", "cap-b")["username"], "b")
        with self.assertRaises(RuntimeError): vault.get(1, "owner", "profile-1-v1")
    def test_restarted_registration_rejects_stale_binding(self):
        from app.worker_channel import WorkerCredentialChannel
        from app.ephemeral_credentials import EphemeralCredentialVault
        channel = WorkerCredentialChannel(vault=EphemeralCredentialVault(), lookup_execution=lambda _: None, session_valid=lambda _: True)
        channel.configure("a", "cap-a")
        old = channel.incarnation("a")
        channel.register("a", "cap-new")
        with self.assertRaises(RuntimeError): channel.bind(1, "owner", expected_worker_id="a", expected_incarnation=old)
