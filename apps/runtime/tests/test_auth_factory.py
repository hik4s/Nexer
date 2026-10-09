import unittest
from unittest.mock import Mock

from auth_guard import FormAuthenticationRenewal, build_auth_guard


class BuildAuthenticationGuardTests(unittest.TestCase):
    def test_builds_guard_with_form_renewal(self):
        provider = Mock()

        guard = build_auth_guard(
            {
                "login_selectors": ["#login"],
                "renewal": {
                    "login_url": "https://example.test/login",
                    "username_selector": "#username",
                    "password_selector": "#password",
                    "submit_selector": "#submit",
                    "success_selector": "#logout",
                    "username_ref": "portal.username",
                    "password_ref": "portal.password",
                },
            },
            credential_provider=provider,
        )

        self.assertIsNotNone(guard)
        self.assertIsInstance(guard.renew, FormAuthenticationRenewal)

    def test_returns_none_without_authentication_config(self):
        self.assertIsNone(build_auth_guard(None, credential_provider=Mock()))


if __name__ == "__main__":
    unittest.main()
