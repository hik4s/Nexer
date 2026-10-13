import unittest
from unittest.mock import Mock

from actions import ActionExecutionError, create_default_registry
from context import ExecutionContext
from recipe import RecipeValidationError, validate_recipe
from resolver import VariableResolver, VariableResolutionError


class RecordedControlTests(unittest.TestCase):
    def test_explicit_empty_input_is_distinct_from_missing_input(self):
        declarations = {"text": {"type": "string", "required": True, "allow_empty": True}}
        resolver = VariableResolver(declarations=declarations, values={"text": ""})
        resolver.validate_required()
        self.assertEqual(resolver.resolve("{{text}}"), "")
        with self.assertRaisesRegex(VariableResolutionError, "MISSING_VARIABLE"):
            VariableResolver(declarations=declarations, values={}).validate_required()

    def test_close_tab_is_idempotent_when_the_previous_click_closed_the_popup(self):
        closed = Mock()
        opened = Mock()
        closed.is_closed.return_value = True
        opened.is_closed.return_value = False
        closed.context.pages = [opened]
        context = ExecutionContext(page=closed, variables={}, downloads_dir="temp")
        create_default_registry().execute("close_tab", {"id": "close"}, context)
        self.assertIs(context.page, opened)
        closed.close.assert_not_called()

    def test_checkbox_is_set_from_execution_value_in_nested_frame(self):
        page = Mock()
        context = ExecutionContext(page=page, variables={"enabled": False}, downloads_dir="temp")
        create_default_registry().execute("check", {"id": "check", "selector": "input", "frames": ["iframe"], "value": "{{enabled}}"}, context)
        page.frame_locator.assert_called_once_with("iframe")
        page.frame_locator.return_value.locator.return_value.set_checked.assert_called_once_with(False, timeout=30000)

    def test_checkbox_rejects_string_boolean_instead_of_treating_it_as_true(self):
        context = ExecutionContext(page=Mock(), variables={}, downloads_dir="temp")
        with self.assertRaisesRegex(ActionExecutionError, "CHECK_VALUE_INVALID"):
            create_default_registry().execute("check", {"id": "check", "selector": "input", "value": "false"}, context)

    def test_invalid_scroll_and_frame_metadata_are_rejected(self):
        for step in ({"action": "scroll", "selector": "html", "x": 0, "y": "secret"},
                     {"action": "click", "selector": "button", "frames": "iframe"}):
            with self.subTest(step=step), self.assertRaises(RecipeValidationError):
                validate_recipe({"schema_version": 1, "name": "Invalid", "variables": {},
                    "steps": [{"id": "one", **step}], "output": {"type": "file"}})
