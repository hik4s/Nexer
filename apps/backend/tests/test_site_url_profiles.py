import unittest
from app.schemas_login_profile import LoginConfiguration, SuccessRule

class ProfileRouteUrlTests(unittest.TestCase):
    def test_login_and_success_routes_retain_hash_in_same_origin(self):
        configuration = LoginConfiguration(login_url="https://site.invalid/#/login", success_rule=SuccessRule(kind="url", url="https://site.invalid/#/home"))
        self.assertEqual(configuration.login_url, "https://site.invalid/#/login")
        self.assertEqual(configuration.allowed_origins, ["https://site.invalid"])
        self.assertEqual(configuration.success_rule.url, "https://site.invalid/#/home")

    def test_allowed_origin_cannot_contain_an_application_route(self):
        with self.assertRaises(ValueError): LoginConfiguration(login_url="https://site.invalid/#/login", allowed_origins=["https://site.invalid/#/home"])
