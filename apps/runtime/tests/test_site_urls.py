import unittest
from site_urls import validate_site_url, site_origin

class SiteUrlTests(unittest.TestCase):
    def test_https_application_route_is_preserved(self):
        value = "https://indicadoresenergisaess.scl.corp/sgind/#/relatatendtodasocorrencias"
        self.assertEqual(validate_site_url(value), value)
        self.assertEqual(site_origin(value), ("https", "indicadoresenergisaess.scl.corp", 443))

    def test_normalizes_host_and_default_port_without_changing_route(self):
        self.assertEqual(validate_site_url("https://SITE.invalid:443/#/report_1"), "https://site.invalid/#/report_1")
        self.assertEqual(validate_site_url("http://[::1]:8765/#/report"), "http://[::1]:8765/#/report")
        self.assertEqual(site_origin("https://site.invalid/api?filter=current"), ("https", "site.invalid", 443))

    def test_rejects_credentials_queries_and_non_route_fragments(self):
        for value in ("http://site.invalid/", "https://@site.invalid/", "https://user:canary@site.invalid/", "https://site.invalid/?token=canary", "https://site.invalid/#token=canary", "https://site.invalid/#/report?token=canary", "https://site.invalid:0/", "javascript:alert(1)"):
            with self.subTest(kind=value.split(":")[0]), self.assertRaises(ValueError):
                validate_site_url(value)

    def test_recipe_site_url_rejects_secret_query_configuration(self):
        from recipe import validate_recipe, RecipeValidationError
        recipe = {"schema_version": 1, "name": "Flow", "site_url": "https://site.invalid/?token=canary", "variables": {}, "steps": [{"id": "open", "action": "navigate", "url": "https://site.invalid/"}], "output": {"type": "file"}}
        with self.assertRaises(RecipeValidationError): validate_recipe(recipe)
