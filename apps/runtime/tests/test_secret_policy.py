import unittest
from unittest.mock import Mock

from credentials import CredentialResolutionError
from resolver import VariableResolutionError, VariableResolver


class ResolverSecretPolicyTests(unittest.TestCase):
    def test_secret_variable_requires_credential_reference(self):
        provider = Mock()
        provider.get.return_value = "secret-value"

        resolver = VariableResolver(
            declarations={
                "password": {
                    "type": "string",
                    "required": True,
                    "secret": True,
                }
            },
            values={
                "password": {
                    "credential_ref": "nexer/sgind/password",
                }
            },
            secret_provider=provider,
        )

        self.assertEqual(resolver.resolve("{{password}}"), "secret-value")
        provider.get.assert_called_once_with("nexer/sgind/password")

    def test_secret_variable_rejects_inline_value(self):
        resolver = VariableResolver(
            declarations={
                "password": {
                    "type": "string",
                    "required": True,
                    "secret": True,
                }
            },
            values={"password": "super-secret"},
        )

        with self.assertRaises(VariableResolutionError) as raised:
            resolver.resolve("{{password}}")

        self.assertIn("SECRET_VALUE_INLINE_FORBIDDEN", str(raised.exception))
        self.assertNotIn("super-secret", str(raised.exception))

    def test_missing_credential_does_not_expose_secret(self):
        provider = Mock()
        provider.get.side_effect = CredentialResolutionError("CREDENTIAL_NOT_FOUND")

        resolver = VariableResolver(
            declarations={
                "password": {
                    "type": "string",
                    "required": True,
                    "secret": True,
                }
            },
            values={
                "password": {
                    "credential_ref": "nexer/sgind/password",
                }
            },
            secret_provider=provider,
        )

        with self.assertRaises(VariableResolutionError) as raised:
            resolver.resolve("{{password}}")

        self.assertEqual(str(raised.exception), "CREDENTIAL_NOT_FOUND")


if __name__ == "__main__":
    unittest.main()
