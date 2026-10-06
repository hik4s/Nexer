import unittest
from unittest.mock import patch

from credentials import (
    CredentialResolutionError,
    KeyringCredentialProvider,
)


class KeyringCredentialProviderTests(unittest.TestCase):
    @patch("credentials.keyring.get_password")
    def test_reads_secret_by_reference_without_logging_value(self, get_password):
        get_password.return_value = "very-secret"

        provider = KeyringCredentialProvider()
        value = provider.get("relatpy/sgind/password")

        self.assertEqual(value, "very-secret")
        get_password.assert_called_once_with(
            "RelatPy",
            "relatpy/sgind/password",
        )

    @patch("credentials.keyring.get_password")
    def test_missing_secret_returns_safe_error(self, get_password):
        get_password.return_value = None

        provider = KeyringCredentialProvider()

        with self.assertRaises(CredentialResolutionError) as raised:
            provider.get("relatpy/sgind/password")

        self.assertEqual(str(raised.exception), "CREDENTIAL_NOT_FOUND")


if __name__ == "__main__":
    unittest.main()
