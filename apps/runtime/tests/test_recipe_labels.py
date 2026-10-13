import unittest
from recipe import RecipeValidationError, validate_recipe

class RecipeLabelTests(unittest.TestCase):
    def test_display_name_is_metadata_only(self):
        recipe = {"schema_version": 1, "name": "Labels", "variables": {"input_001": {"type": "string", "label": "Email do responsável"}}, "steps": [{"id": "fill", "action": "fill", "selector": "input", "value": "{{input_001}}"}], "output": {"type": "file"}}
        normalized = validate_recipe(recipe)
        self.assertEqual(normalized["variables"]["input_001"]["label"], "Email do responsável")
        self.assertEqual(normalized["steps"][0]["value"], "{{input_001}}")
        for invalid in (123, {}, None, "x" * 101):
            recipe["variables"]["input_001"]["label"] = invalid
            with self.subTest(label=invalid), self.assertRaisesRegex(RecipeValidationError, "VARIABLE_LABEL_INVALID"):
                validate_recipe(recipe)
