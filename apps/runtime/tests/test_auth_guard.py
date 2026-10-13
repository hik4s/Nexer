import unittest
from unittest.mock import Mock

from auth_guard import AuthenticationGuard, AuthenticationRequired


class FakePage:
    def __init__(self, url="https://example.test/report", login_visible=False):
        self.url = url
        self.login_visible = login_visible

    def locator(self, selector):
        locator = Mock()
        locator.is_visible.return_value = self.login_visible and selector == "#login"
        return locator


class AuthenticationGuardTests(unittest.TestCase):
    def test_allows_authenticated_page(self):
        page = FakePage(login_visible=False)
        renew = Mock()

        guard = AuthenticationGuard(
            login_selectors=["#login"],
            renew=renew,
        )

        self.assertEqual(guard.ensure_authenticated(page), page)
        renew.assert_not_called()

    def test_renews_once_when_login_is_detected(self):
        page = FakePage(login_visible=True)
        renew = Mock(return_value=True)

        guard = AuthenticationGuard(
            login_selectors=["#login"],
            renew=renew,
        )

        guard.ensure_authenticated(page)
        self.assertEqual(renew.call_count, 1)

        page.login_visible = False
        guard.ensure_authenticated(page)
        self.assertEqual(renew.call_count, 1)

    def test_raises_when_renewal_cannot_restore_session(self):
        page = FakePage(login_visible=True)
        renew = Mock(return_value=False)

        guard = AuthenticationGuard(
            login_selectors=["#login"],
            renew=renew,
        )

        with self.assertRaises(AuthenticationRequired):
            guard.ensure_authenticated(page)

    def test_never_exposes_credential_values_in_error(self):
        page = FakePage(login_visible=True)
        renew = Mock(side_effect=RuntimeError("very-secret"))

        guard = AuthenticationGuard(
            login_selectors=["#login"],
            renew=renew,
        )

        with self.assertRaises(AuthenticationRequired) as raised:
            guard.ensure_authenticated(page)

        self.assertNotIn("very-secret", str(raised.exception))


if __name__ == "__main__":
    unittest.main()
