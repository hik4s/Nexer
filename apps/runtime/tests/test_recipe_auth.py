import unittest

from recipe import RecipeValidationError, validate_recipe


class RecipeAuthenticationValidationTests(unittest.TestCase):
    def _recipe(self, authentication):
        return {
            "schema_version": 1,
            "name": "Auth recipe",
            "variables": {},
            "steps": [
                {
                    "id": "open",
                    "action": "navigate",
                    "url": "https://example.test/report",
                }
            ],
            "authentication": authentication,
            "output": {"type": "file"},
        }

    def test_valid_session_authentication_is_accepted(self):
        recipe = self._recipe(
            {
                "session_ref": "portal-a",
                "login_selectors": ["#login"],
            }
        )

        validated = validate_recipe(recipe)

        self.assertEqual(
            validated["authentication"]["session_ref"],
            "portal-a",
        )

    def test_missing_login_selectors_is_rejected(self):
        recipe = self._recipe({"session_ref": "portal-a"})

        with self.assertRaisesRegex(
            RecipeValidationError,
            "AUTH_LOGIN_SELECTORS_REQUIRED",
        ):
            validate_recipe(recipe)

    def test_invalid_form_renewal_is_rejected(self):
        recipe = self._recipe(
            {
                "session_ref": "portal-a",
                "login_selectors": ["#login"],
                "renewal": {
                    "login_url": "https://example.test/login",
                    "username_selector": "#user",
                },
            }
        )

        with self.assertRaisesRegex(
            RecipeValidationError,
            "AUTH_RENEWAL_CONFIG_INVALID",
        ):
            validate_recipe(recipe)

    def test_unsafe_session_reference_is_rejected(self):
        recipe = self._recipe(
            {
                "session_ref": "../portal",
                "login_selectors": ["#login"],
            }
        )

        with self.assertRaisesRegex(
            RecipeValidationError,
            "INVALID_SESSION_REFERENCE",
        ):
            validate_recipe(recipe)


if __name__ == "__main__":
    unittest.main()
