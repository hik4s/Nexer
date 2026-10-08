import json
import unittest
from unittest.mock import patch

from session_store import SessionStateError, SessionStateStore


class SessionStateStoreTests(unittest.TestCase):
    def test_saves_and_loads_state_through_os_keyring(self):
        store = SessionStateStore()
        state = {
            "cookies": [
                {
                    "name": "session",
                    "value": "opaque-token",
                    "domain": "example.test",
                    "path": "/",
                }
            ],
            "origins": [],
        }

        with patch("session_store.keyring.set_password") as set_password, patch(
            "session_store.keyring.get_password",
            return_value=json.dumps(state),
        ):
            store.save("portal-a", state)
            restored = store.load("portal-a")

        set_password.assert_called_once()
        self.assertEqual(restored, state)

    def test_missing_state_returns_none(self):
        store = SessionStateStore()

        with patch("session_store.keyring.get_password", return_value=None):
            self.assertIsNone(store.load("missing"))

    def test_rejects_invalid_reference(self):
        store = SessionStateStore()

        with self.assertRaisesRegex(SessionStateError, "INVALID_SESSION_REFERENCE"):
            store.load("../unsafe")

    def test_rejects_invalid_state(self):
        store = SessionStateStore()

        with self.assertRaisesRegex(SessionStateError, "INVALID_SESSION_STATE"):
            store.save("portal-a", {"cookies": "not-a-list"})

    def test_does_not_expose_state_in_errors(self):
        store = SessionStateStore()
        secret = "opaque-token"

        with patch(
            "session_store.keyring.set_password",
            side_effect=RuntimeError(secret),
        ):
            with self.assertRaises(SessionStateError) as raised:
                store.save("portal-a", {"cookies": []})

        self.assertNotIn(secret, str(raised.exception))


if __name__ == "__main__":
    unittest.main()
