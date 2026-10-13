import json
import unittest
from nexer_recorder.compiler import Recording


class RecordingTests(unittest.TestCase):
    def test_labels_and_download_collection_keep_only_metadata(self):
        recording = Recording("Report")
        recording.accept({"action": "fill", "selector": "input", "label": "Data inicial", "field": {"control": "date"}})
        recording.accept({"action": "download", "selector": "a", "collection": {"rows": "tbody > tr", "name": "td:first-child", "button": "a"}})
        recipe = recording.recipe()
        self.assertEqual(recipe["variables"]["input_001"]["label"], "Data inicial")
        self.assertEqual(recipe["steps"][-1]["collection"]["pattern"], "{{download_pattern_001}}")
        self.assertNotIn("default", json.dumps(recipe))
    def test_field_rules_are_preserved_without_defaults_or_option_values(self):
        recording = Recording("Rules")
        field = {"control": "number", "min": 1, "max": 100, "step": 0.5, "required": True}
        recording.accept({"action": "fill", "selector": "input", "field": field})
        self.assertEqual(recording.recipe()["variables"]["input_001"]["field"], field)
        for extra in ({"value": "recorded-canary"}, {"options": ["recorded-canary"]}, {"default": "recorded-canary"}):
            with self.assertRaises(ValueError):
                recording.accept({"action": "fill", "selector": "input", "field": {**field, **extra}})
        self.assertNotIn("recorded-canary", json.dumps(recording.recipe()))

    def test_required_and_temporal_rules_preserve_constraints_without_defaults(self):
        recording = Recording("Rules")
        recording.accept({"action": "fill", "selector": "input:nth-of-type(1)", "field": {"control": "email", "required": True, "max_length": 80}})
        recording.accept({"action": "fill", "selector": "#period_start", "parameter": "period_start", "field": {"control": "date", "min": "2026-01-01", "max": "2030-12-31", "step": 2}})
        recipe = recording.recipe()
        self.assertNotIn("allow_empty", recipe["variables"]["input_001"])
        self.assertEqual(recipe["variables"]["period_start"]["field"]["min"], "2026-01-01")
        self.assertNotIn("default", json.dumps(recipe))

    def test_distinct_radio_groups_and_checkbox_occurrences_get_distinct_inputs(self):
        recording = Recording("States")
        recording.accept({"action": "choose_radio", "selector": "form", "group_index": 0})
        recording.accept({"action": "choose_radio", "selector": "form", "group_index": 1})
        recording.accept({"action": "check", "selector": "input"})
        recording.accept({"action": "click", "selector": "button"})
        recording.accept({"action": "check", "selector": "input"})
        steps = recording.recipe()["steps"]
        self.assertNotEqual(steps[1]["value"], steps[2]["value"])
        self.assertNotEqual(steps[3]["value"], steps[5]["value"])

    def test_browser_confirmed_download_promotes_only_the_exact_last_click(self):
        recording = Recording("Async export")
        recording.accept({"action": "click", "selector": "#export"})
        recording.promote_recent_click_to_download(step_index=1)
        recipe = recording.recipe()
        self.assertEqual(recipe["steps"][1]["action"], "download")
        self.assertEqual(recipe["steps"][1]["selector"], "#export")
        self.assertEqual(recipe["steps"][1]["filename"], "{{download_file_001}}")
        self.assertNotIn("private-export-name.csv", str(recipe))

    def test_browser_confirmed_download_rejects_intervening_click(self):
        recording = Recording("Async export")
        recording.accept({"action": "click", "selector": "#export"})
        recording.accept({"action": "click", "selector": "#other"})
        with self.assertRaisesRegex(ValueError, "RECORDER_DOWNLOAD_UNSUPPORTED"):
            recording.promote_recent_click_to_download(step_index=1)
        self.assertEqual([step["action"] for step in recording.recipe()["steps"]], ["navigate", "click", "click"])

    def test_delayed_download_never_rewrites_an_unrelated_click(self):
        recording = Recording("Download")
        recording.accept({"action": "click", "selector": "#export"})
        recording.accept({"action": "click", "selector": "#next"})
        with self.assertRaisesRegex(ValueError, "RECORDER_DOWNLOAD_UNSUPPORTED"):
            recording.mark_download()
        self.assertEqual(recording.recipe()["steps"][-1]["action"], "click")
        recording.accept({"action": "download", "selector": "#known_download"})
        recording.mark_download()
        self.assertEqual(recording.recipe()["steps"][-1]["filename"], "{{download_file_001}}")

    def test_same_semantic_field_in_different_frame_gets_a_separate_input(self):
        recording = Recording("Frames")
        recording.accept({"action": "fill", "selector": "#company", "parameter": "company"})
        for _ in range(2):
            recording.accept({"action": "fill", "selector": "#company", "parameter": "company", "frames": ["iframe"]})
        self.assertEqual(recording.recipe()["steps"][-1]["value"], "{{company_002}}")

    def test_controls_frames_and_context_actions_keep_only_parameters(self):
        recording = Recording("Controls")
        recording.accept({"action": "check", "selector": "input:nth-of-type(1)", "frames": ["iframe:nth-of-type(1)"]})
        recording.accept({"action": "set_value", "selector": "input:nth-of-type(2)", "input_type": "range"})
        recording.accept({"action": "choose", "selector": "div:nth-of-type(1)"})
        recording.accept({"action": "scroll", "selector": "html", "x": 0, "y": 500})
        recording.accept({"action": "switch_tab", "index": 1})
        recipe = recording.recipe()
        self.assertEqual(recipe["variables"]["input_001"]["type"], "boolean")
        self.assertEqual(recipe["steps"][1]["value"], "{{input_001}}")
        self.assertEqual(recipe["steps"][1]["frames"], ["iframe:nth-of-type(1)"])
        self.assertEqual(recipe["steps"][-1]["action"], "switch_tab")

    def test_generated_parameter_does_not_collide_with_existing_name(self):
        recording = Recording("Relatório")
        recording.accept({"action": "fill", "selector": "#first", "parameter": "input_002"})
        recording.accept({"action": "fill", "selector": "#second"})
        self.assertEqual(recording.recipe()["steps"][2]["value"], "{{input_001}}")

    def test_date_location_becomes_required_parameter_without_recorded_value(self):
        recording = Recording("Relatório")
        recording.accept({"action": "fill", "selector": "#period_start", "parameter": "period_start"})
        recording.accept({"action": "click", "selector": "#export"})
        recipe = recording.recipe()
        self.assertEqual(recipe["steps"][1]["value"], "{{period_start}}")
        self.assertEqual(recipe["variables"]["period_start"], {"type": "string", "required": True, "format": "date", "field": {"control": "date"}})

    def test_value_bearing_events_are_rejected_before_accumulation(self):
        recording = Recording("Relatório")
        with self.assertRaisesRegex(ValueError, "RECORDER_EVENT_INVALID"):
            recording.accept({"action": "fill", "selector": "#date", "value": "synthetic-canary"})
        self.assertNotIn("synthetic-canary", json.dumps(recording.recipe()))
        self.assertEqual(len(recording.recipe()["steps"]), 1)

    def test_consecutive_input_events_coalesce_without_losing_action_order(self):
        recording = Recording("Relatório")
        for _ in range(3):
            recording.accept({"action": "fill", "selector": "#date"})
        recording.accept({"action": "click", "selector": "#export"})
        recording.accept({"action": "fill", "selector": "#date"})
        recipe = recording.recipe()
        self.assertEqual([step["action"] for step in recipe["steps"]], ["navigate", "fill", "click", "fill"])
        self.assertEqual(recipe["steps"][1]["value"], recipe["steps"][3]["value"])
