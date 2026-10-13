import json
import unittest

from nexer_recorder.compiler import Recording
from nexer_recorder.smart_waits import optimize_recipe


class SmartWaitTests(unittest.TestCase):
    def test_generic_flow_without_dates_or_downloads(self):
        recording = Recording("General task")
        recording.accept({"action": "click", "selector": "#menu"})
        recording.accept({"action": "fill", "selector": "#search"})
        result = optimize_recipe(recording.recipe())
        self.assertEqual([step["action"] for step in result["steps"]],
                         ["navigate", "wait_for", "click", "wait_for", "fill"])
        self.assertEqual(result["variables"]["input_001"]["field"]["control"], "text")
        self.assertFalse(any("period" in key for key in result["variables"]))
        self.assertEqual(result["output"]["type"], "none")

    def test_download_waits_until_enabled(self):
        recording = Recording("Export")
        recording.accept({"action": "download", "selector": "button.export"})
        result = optimize_recipe(recording.recipe())
        self.assertEqual(result["steps"][1]["state"], "enabled")
        self.assertEqual(result["steps"][2]["action"], "download")
        self.assertEqual(result["steps"][1]["learning"], {"source": "automatic", "confidence": "medium"})
        self.assertEqual(result["output"]["type"], "file")

    def test_async_collection_uses_existing_polling_not_stale_button(self):
        recording = Recording("Central")
        recording.accept({"action": "download", "selector": "table > tr:first-child > button",
                          "collection": {"rows": "table tr", "name": "td:first-child", "button": "button"}})
        result = optimize_recipe(recording.recipe())
        self.assertEqual([step["action"] for step in result["steps"]], ["navigate", "download"])

    def test_manual_wait_takes_priority(self):
        recording = Recording("Manual")
        recording.accept({"action": "wait_for", "selector": "#export", "state": "enabled",
                          "learning": {"source": "manual", "confidence": "high"}})
        recording.accept({"action": "download", "selector": "#export"})
        result = optimize_recipe(recording.recipe())
        self.assertEqual(len(result["steps"]), 3)
        self.assertEqual(result["steps"][1]["learning"]["source"], "manual")

    def test_idempotent_and_does_not_capture_values(self):
        recording = Recording("No secrets")
        recording.accept({"action": "fill", "selector": "#query"})
        recording.accept({"action": "click", "selector": "#go"})
        first = optimize_recipe(recording.recipe())
        self.assertEqual(optimize_recipe(first), first)
        self.assertNotIn("private-value-canary", json.dumps(first))

    def test_frames_and_unique_ids(self):
        recording = Recording("Frames")
        recording.accept({"action": "click", "selector": "button", "frames": ["iframe"]})
        result = optimize_recipe(recording.recipe())
        self.assertEqual(result["steps"][1]["frames"], ["iframe"])
        self.assertEqual(len({step["id"] for step in result["steps"]}), len(result["steps"]))


if __name__ == "__main__":
    unittest.main()
