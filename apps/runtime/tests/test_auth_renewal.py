import unittest
from unittest.mock import Mock

from auth_guard import AuthenticationRenewalError, FormAuthenticationRenewal


class FormAuthenticationRenewalTests(unittest.TestCase):
    def test_logs_in_with_credentials_without_logging_values(self):
        page = Mock()
        locators = {selector: Mock() for selector in ("#username", "#password", "#submit", "#logout")}
        page.locator.side_effect = locators.__getitem__
        provider = Mock()
        provider.get.side_effect = ["user-value", "password-value"]

        renewal = FormAuthenticationRenewal(
            login_url="https://example.test/login",
            username_selector="#username",
            password_selector="#password",
            submit_selector="#submit",
            success_selector="#logout",
            username_ref="portal.username",
            password_ref="portal.password",
            credential_provider=provider,
        )

        self.assertTrue(renewal(page))

        page.goto.assert_called_once_with(
            "https://example.test/login",
            wait_until="domcontentloaded",
        )
        page.locator.assert_any_call("#username")
        page.locator.assert_any_call("#password")
        page.locator.assert_any_call("#submit")
        page.locator.assert_any_call("#logout")

        page.locator("#username").fill.assert_called_once_with("user-value")
        page.locator("#password").fill.assert_called_once_with("password-value")
        page.locator("#submit").click.assert_called_once()
        page.locator("#logout").wait_for.assert_called_once_with(
            state="visible",
            timeout=30000,
        )

    def test_does_not_expose_credential_values_when_provider_fails(self):
        page = Mock()
        provider = Mock()
        provider.get.side_effect = RuntimeError("password-value")

        renewal = FormAuthenticationRenewal(
            login_url="https://example.test/login",
            username_selector="#username",
            password_selector="#password",
            submit_selector="#submit",
            success_selector="#logout",
            username_ref="portal.username",
            password_ref="portal.password",
            credential_provider=provider,
        )

        with self.assertRaises(AuthenticationRenewalError) as raised:
            renewal(page)

        self.assertNotIn("password-value", str(raised.exception))


if __name__ == "__main__":
    unittest.main()
