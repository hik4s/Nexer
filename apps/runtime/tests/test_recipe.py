import unittest


from recipe import RecipeValidationError, validate_recipe


class RecipeValidationTests(unittest.TestCase):
    def test_valid_recipe_is_normalized(self):
        recipe = {
            "schema_version": 1,
            "name": "Relatorio piloto",
            "variables": {
                "period_start": {"type": "string", "required": True},
            },
            "steps": [
                {
                    "id": "open",
                    "action": "navigate",
                    "url": "https://example.test/report",
                },
                {
                    "id": "fill_start",
                    "action": "fill",
                    "selector": "#start",
                    "value": "{{period_start}}",
                },
            ],
            "output": {
                "type": "file",
                "expected_extension": ".xlsx",
            },
        }

        validated = validate_recipe(recipe)

        self.assertEqual(validated["schema_version"], 1)
        self.assertEqual(validated["name"], "Relatorio piloto")
        self.assertEqual(len(validated["steps"]), 2)


    def test_navigate_accepts_url_provided_by_declared_variable(self):
        recipe = {
            "schema_version": 1,
            "name": "URL parametrizada",
            "variables": {
                "base_url": {"type": "string", "required": True},
            },
            "steps": [
                {
                    "id": "open",
                    "action": "navigate",
                    "url": "{{base_url}}",
                }
            ],
            "output": {"type": "file"},
        }

        validated = validate_recipe(recipe)

        self.assertEqual(validated["steps"][0]["url"], "{{base_url}}")

    def test_unknown_action_is_rejected(self):
        recipe = {
            "schema_version": 1,
            "name": "Inválida",
            "variables": {},
            "steps": [{"id": "x", "action": "run_python", "code": "print(1)"}],
            "output": {"type": "file"},
        }

        with self.assertRaises(RecipeValidationError) as raised:
            validate_recipe(recipe)

        self.assertIn("UNKNOWN_ACTION", str(raised.exception))

    def test_undeclared_variable_is_rejected(self):
        recipe = {
            "schema_version": 1,
            "name": "Inválida",
            "variables": {},
            "steps": [
                {
                    "id": "fill_start",
                    "action": "fill",
                    "selector": "#start",
                    "value": "{{period_start}}",
                }
            ],
            "output": {"type": "file"},
        }

        with self.assertRaises(RecipeValidationError) as raised:
            validate_recipe(recipe)

        self.assertIn("UNDECLARED_VARIABLE", str(raised.exception))

    def test_action_specific_requirements_are_enforced(self):
        recipe = {
            "schema_version": 1,
            "name": "Inválida",
            "variables": {},
            "steps": [{"id": "click", "action": "click"}],
            "output": {"type": "file"},
        }

        with self.assertRaises(RecipeValidationError) as raised:
            validate_recipe(recipe)

        self.assertIn("SELECTOR_REQUIRED", str(raised.exception))


if __name__ == "__main__":
    unittest.main()
