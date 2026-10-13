"""Trusted login behavior; browser and channel boundaries use synthetic doubles."""
import unittest
import traceback
import corporate_auth


class Locator:
    def __init__(self, page, selector):
        self.page, self.selector = page, selector

    def fill(self, value, **kwargs):
        self.page.fills.append((self.selector, value))
        if self.page.fill_error:
            raise ValueError("synthetic-password-canary")

    def click(self, **kwargs):
        self.page.submitted = True
        if self.page.success:
            self.page.url = self.page.home_url

    def is_visible(self):
        return self.page.submitted and self.page.success and self.selector == "app-home-page"

    def count(self):
        return 0 if self.page.submitted and self.page.success else 1

    def get_attribute(self, name):
        return self.page.form_action


class Page:
    def __init__(self, system="SGIND"):
        self.url = ""
        self.home_url = f"https://indicadoresenergisaess.scl.corp/{system.lower()}/#/home"
        self.redirect = None
        self.form_action = None
        self.fills = []
        self.submitted = False
        self.success = True
        self.fill_error = False

    def goto(self, url, **kwargs):
        self.url = self.redirect or url

    def locator(self, selector):
        return Locator(self, selector)

    def wait_for_timeout(self, milliseconds):
        pass


class Client:
    def __init__(self):
        self.values = {}
        self.calls = []

    def resolve(self, execution_id, system):
        self.calls.append((execution_id, system))
        self.values = {"username": "synthetic-user", "password": "synthetic-password-canary"}
        return self.values


class CorporateLoginTests(unittest.TestCase):
    def login(self, page, client, **kwargs):
        self.assertTrue(hasattr(corporate_auth, "authenticate_corporate"),
                        "Trusted corporate login is not implemented")
        return corporate_auth.authenticate_corporate(page, client, 7, "SGIND",
                                                     timeout_ms=50, **kwargs)

    def test_each_system_uses_its_own_trusted_form_and_discards_credentials(self):
        self.assertTrue(hasattr(corporate_auth, "authenticate_corporate"),
                        "Trusted corporate login is not implemented")
        for system, form in (("SGIND", "form#idFormLogin"), ("IQOS", 'form[name="form"]')):
            page, client = Page(system), Client()
            corporate_auth.authenticate_corporate(page, client, 7, system, timeout_ms=5)
            self.assertEqual(client.calls, [(7, system)] * 4)
            self.assertEqual(page.fills, [
                (form + ' input[name="cre_username"]', "synthetic-user"),
                (form + ' input[name="cre_password"][type="password"]', "synthetic-password-canary")])
            self.assertEqual(client.values, {})
            self.assertEqual(page.url, page.home_url)

    def test_external_redirect_never_resolves_or_fills_credentials(self):
        page, client = Page(), Client()
        page.redirect = "https://evil.example/login"
        with self.assertRaisesRegex(RuntimeError, "^CORPORATE_LOGIN_FAILED$"):
            self.login(page, client)
        self.assertEqual(client.calls, [])
        self.assertEqual(page.fills, [])

    def test_wrong_application_or_nonlogin_page_never_resolves_credentials(self):
        for destination in ("https://indicadoresenergisaess.scl.corp/iqos/#/login",
                            "https://indicadoresenergisaess.scl.corp/sgind/#/report"):
            page, client = Page(), Client()
            page.redirect = destination
            with self.assertRaisesRegex(RuntimeError, "^CORPORATE_LOGIN_FAILED$"):
                self.login(page, client)
            self.assertEqual(client.calls, [])

    def test_external_form_action_is_rejected_before_resolving(self):
        page, client = Page(), Client()
        page.form_action = "https://evil.example/collect"
        with self.assertRaisesRegex(RuntimeError, "^CORPORATE_LOGIN_FAILED$"):
            self.login(page, client)
        self.assertEqual(client.calls, [])

    def test_fill_failure_discards_values_and_suppresses_browser_error(self):
        page, client = Page(), Client()
        page.fill_error = True
        with self.assertRaisesRegex(RuntimeError, "^CORPORATE_LOGIN_FAILED$") as raised:
            self.login(page, client)
        self.assertEqual(client.values, {})
        self.assertFalse(page.submitted)
        rendered = "".join(traceback.format_exception(raised.exception))
        self.assertNotIn("synthetic-password-canary", rendered)

    def test_login_without_home_evidence_fails(self):
        page, client = Page(), Client()
        page.success = False
        with self.assertRaisesRegex(RuntimeError, "^CORPORATE_LOGIN_FAILED$"):
            self.login(page, client)
        self.assertEqual(client.values, {})

    def test_cancellation_before_login_does_not_retrieve_credentials(self):
        page, client = Page(), Client()
        with self.assertRaisesRegex(RuntimeError, "^CORPORATE_LOGIN_FAILED$"):
            self.login(page, client, cancellation_requested=lambda: True)
        self.assertEqual(client.calls, [])
        self.assertEqual(page.fills, [])

    def test_cancellation_after_username_prevents_password_and_submit(self):
        page, client = Page(), Client()
        with self.assertRaisesRegex(RuntimeError, "^CORPORATE_LOGIN_FAILED$"):
            self.login(page, client, cancellation_requested=lambda: bool(page.fills))
        self.assertEqual(len(page.fills), 1)
        self.assertFalse(page.submitted)
        self.assertEqual(client.values, {})

    def test_invalid_timeout_fails_with_constant_error_before_navigation(self):
        self.assertTrue(hasattr(corporate_auth, "authenticate_corporate"))
        for invalid in (None, "500", True, 0, -1, 60001):
            page, client = Page(), Client()
            with self.assertRaisesRegex(RuntimeError, "^CORPORATE_LOGIN_FAILED$"):
                corporate_auth.authenticate_corporate(page, client, 7, "SGIND",
                                                     timeout_ms=invalid)
            self.assertEqual(page.url, "")
            self.assertEqual(client.calls, [])

    def test_channel_revocation_before_password_stops_submission(self):
        class RevokedClient(Client):
            def resolve(self, execution_id, system):
                if self.calls:
                    raise RuntimeError("synthetic-password-canary")
                return super().resolve(execution_id, system)
        page, client = Page(), RevokedClient()
        with self.assertRaisesRegex(RuntimeError, "^CORPORATE_LOGIN_FAILED$"):
            self.login(page, client)
        self.assertEqual(len(page.fills), 1)
        self.assertFalse(page.submitted)
        self.assertEqual(client.values, {})
