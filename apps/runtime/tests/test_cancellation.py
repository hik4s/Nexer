import unittest

from context import ExecutionContext
from runner import RecipeRunner


class FakePage:
    def __init__(self):
        self.calls = []

    def goto(self, url, **kwargs):
        self.calls.append(("goto", url))

    def fill(self, value, **kwargs):
        self.calls.append(("fill", value))

    def locator(self, selector):
        return self

    def click(self, **kwargs):
        self.calls.append(("click",))


class RunnerCancellationTests(unittest.TestCase):
    def test_runner_stops_before_next_step_when_cancellation_is_requested(self):
        cancelled = {"value": False}
        page = FakePage()

        def emit(event):
            if event["type"] == "checkpoint":
                cancelled["value"] = True

        context = ExecutionContext(
            page=page,
            variables={},
            downloads_dir=".",
            emit=emit,
            cancellation_requested=lambda: cancelled["value"],
        )

        recipe = {
            "schema_version": 1,
            "name": "Cancel",
            "variables": {},
            "steps": [
                {
                    "id": "open",
                    "action": "navigate",
                    "url": "https://example.test",
                },
                {
                    "id": "second",
                    "action": "click",
                    "selector": "#next",
                },
            ],
            "output": {"type": "file"},
        }

        result = RecipeRunner().run(recipe, context)

        self.assertTrue(result.cancelled)
        self.assertEqual(result.completed_steps, 1)
        self.assertIsNone(result.failed_step_id)
        self.assertEqual(page.calls, [("goto", "https://example.test")])


if __name__ == "__main__":
    unittest.main()
