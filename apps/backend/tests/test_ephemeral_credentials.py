import unittest

class EphemeralCredentialsTests(unittest.TestCase):
    def setUp(self):
        from app.ephemeral_credentials import EphemeralCredentialVault
        self.now = 100.0
        self.vault = EphemeralCredentialVault(clock=lambda: self.now)
        self.systems = {"SGIND": {"username": "synthetic-user", "password": "synthetic-secret"}}

    def test_isolation_and_defensive_copies(self):
        self.vault.put(1, "owner-a", self.systems, ttl_seconds=60)
        self.systems["SGIND"]["password"] = "changed"
        found = self.vault.get(1, "owner-a", "SGIND")
        self.assertEqual(found["password"], "synthetic-secret")
        found["password"] = "changed-again"
        self.assertEqual(self.vault.get(1, "owner-a", "SGIND")["password"], "synthetic-secret")
        for args in [(2, "owner-a", "SGIND"), (1, "owner-b", "SGIND"), (1, "owner-a", "IQOS")]:
            with self.assertRaisesRegex(RuntimeError, "^CREDENTIALS_UNAVAILABLE$"):
                self.vault.get(*args)

    def test_expiration_and_restart_fail_closed(self):
        self.vault.put(1, "owner-a", self.systems, ttl_seconds=60)
        self.now = 160
        with self.assertRaisesRegex(RuntimeError, "^CREDENTIALS_UNAVAILABLE$"):
            self.vault.get(1, "owner-a", "SGIND")
        from app.ephemeral_credentials import EphemeralCredentialVault
        with self.assertRaises(RuntimeError):
            EphemeralCredentialVault().get(1, "owner-a", "SGIND")

    def test_revoke_execution_and_owner(self):
        for execution, owner in [(1, "a"), (2, "a"), (3, "b")]:
            self.vault.put(execution, owner, self.systems, ttl_seconds=60)
        self.vault.revoke(1)
        self.vault.revoke_owner("a")
        for execution in (1, 2):
            with self.assertRaises(RuntimeError):
                self.vault.get(execution, "a", "SGIND")
        self.assertEqual(self.vault.get(3, "b", "SGIND")["username"], "synthetic-user")

    def test_repr_and_invalid_payload_do_not_expose_values(self):
        self.vault.put(1, "a", self.systems, ttl_seconds=60)
        self.assertNotIn("synthetic", repr(self.vault))
        for payload in [{"OTHER": self.systems["SGIND"]}, {"SGIND": {"password": "synthetic-secret"}}, {}]:
            with self.assertRaisesRegex(ValueError, "^INVALID_CREDENTIAL_PAYLOAD$"):
                self.vault.put(2, "a", payload, ttl_seconds=60)
        with self.assertRaises(ValueError):
            self.vault.put(2, "a", self.systems, ttl_seconds=0)

    def test_capacity_and_periodic_expiry_cleanup(self):
        from app.ephemeral_credentials import EphemeralCredentialVault
        vault = EphemeralCredentialVault(clock=lambda: self.now, capacity=1)
        vault.put(1, "a", self.systems, ttl_seconds=60)
        with self.assertRaisesRegex(RuntimeError, "^CREDENTIAL_CAPACITY_EXCEEDED$"):
            vault.put(2, "a", self.systems, ttl_seconds=60)
        self.now = 160
        self.assertEqual(vault.purge_expired(), 1)
        vault.put(2, "a", self.systems, ttl_seconds=60)
        self.assertEqual(vault.get(2, "a", "SGIND")["password"], "synthetic-secret")

    def test_existing_execution_cannot_be_overwritten(self):
        self.vault.put(1, "a", self.systems, ttl_seconds=60)
        with self.assertRaisesRegex(RuntimeError, "^CREDENTIALS_ALREADY_BOUND$"):
            self.vault.put(1, "b", self.systems, ttl_seconds=60)
        self.assertEqual(self.vault.get(1, "a", "SGIND")["password"], "synthetic-secret")
