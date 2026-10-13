import unittest

import corporate_auth


class CorporateLoginDefinitionTests(unittest.TestCase):
    def test_iqos_known_destination_is_permitted(self):
        corporate_auth.validate_corporate_url("IQOS",
            "https://indicadoresenergisaess.scl.corp/iqos/#/home")

    def test_system_cannot_navigate_to_the_other_application(self):
        for system, path in (("SGIND", "/iqos/"), ("IQOS", "/sgind/")):
            with self.assertRaisesRegex(RuntimeError, "^CORPORATE_DESTINATION_FORBIDDEN$"):
                corporate_auth.validate_corporate_url(system,
                    "https://indicadoresenergisaess.scl.corp" + path + "#/home")

    def test_cross_path_alias_and_traversal_are_forbidden(self):
        for path in ("/sgind-evil/", "/sgind/../iqos/", "/sgind/%2e%2e/iqos/",
                     "/sgind/%2f../iqos/", "/SGIND/", "/sgind"):
            with self.assertRaisesRegex(RuntimeError, "^CORPORATE_DESTINATION_FORBIDDEN$"):
                corporate_auth.validate_corporate_url("SGIND",
                    "https://indicadoresenergisaess.scl.corp" + path + "#/home")

    def test_login_definition_uses_stable_selectors_for_each_system(self):
        self.assertTrue(hasattr(corporate_auth, "get_login_definition"),
                        "Trusted login definitions are missing")
        sgind = corporate_auth.get_login_definition("SGIND")
        iqos = corporate_auth.get_login_definition("IQOS")
        self.assertEqual(sgind.form_selector, "form#idFormLogin")
        self.assertEqual(iqos.form_selector, 'form[name="form"]')
        for system, definition in (("sgind", sgind), ("iqos", iqos)):
            self.assertEqual(definition.login_url,
                f"https://indicadoresenergisaess.scl.corp/{system}/#/login")
            self.assertEqual(definition.home_url,
                f"https://indicadoresenergisaess.scl.corp/{system}/#/home")
            self.assertEqual(definition.home_selector, "app-home-page")
            self.assertIn('[name="cre_username"]', definition.username_selector)
            self.assertIn('[name="cre_password"]', definition.password_selector)
            self.assertIn('button[type="submit"]', definition.submit_selector)

    def test_success_requires_exact_home_visible_component_and_no_login_form(self):
        self.assertTrue(hasattr(corporate_auth, "matches_authenticated_home"),
                        "Success evidence matcher is missing")
        for system in ("SGIND", "IQOS"):
            url = f"https://indicadoresenergisaess.scl.corp/{system.lower()}/#/home"
            self.assertTrue(corporate_auth.matches_authenticated_home(system, url,
                home_visible=True, login_form_present=False))
            for home_visible, form_present in ((False, False), (True, True), (False, True)):
                self.assertFalse(corporate_auth.matches_authenticated_home(system, url,
                    home_visible=home_visible, login_form_present=form_present))
            for bad_url in (url.replace("#/home", "#/login"), url + "?unexpected",
                            url.replace(system.lower(), "other"),
                            url.replace(".corp/", ".corp.evil.example/")):
                self.assertFalse(corporate_auth.matches_authenticated_home(system, bad_url,
                    home_visible=True, login_form_present=False))
        self.assertFalse(corporate_auth.matches_authenticated_home("UNKNOWN",
            "https://indicadoresenergisaess.scl.corp/sgind/#/home",
            home_visible=True, login_form_present=False))
