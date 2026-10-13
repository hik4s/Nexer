import json
import unittest
from pathlib import Path

from recipe import validate_recipe


ROOT = Path(__file__).resolve().parents[1]
RECIPE_PATH = ROOT / "recipes" / "pilot-smoke.json"


class PilotRecipeTests(unittest.TestCase):
    def test_pilot_recipe_is_valid_runtime_v1(self):
        recipe = json.loads(RECIPE_PATH.read_text(encoding="utf-8"))

        validated = validate_recipe(recipe)

        self.assertEqual(validated["schema_version"], 1)
        self.assertEqual(validated["name"], "Nexer Local Pilot")
        self.assertEqual(
            [step["action"] for step in validated["steps"]],
            [
                "navigate",
                "fill",
                "click",
                "download",
                "validate_file",
            ],
        )
        self.assertEqual(
            validated["variables"]["company"]["required"],
            True,
        )


if __name__ == "__main__":
    unittest.main()
