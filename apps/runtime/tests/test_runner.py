import unittest


from context import ExecutionContext
from runner import RecipeRunner


class FakePage:
    def locator(self, selector):
        return self

    def click(self):
        pass

    def fill(self, value):
        pass

    def goto(self, url, wait_until="domcontentloaded", timeout=30000):
        pass


class RunnerTests(unittest.TestCase):
    def test_runner_executes_steps_in_order_and_emits_events(self):
        events = []
        context = ExecutionContext(
            page=FakePage(),
            variables={"name": "Kauan"},
            emit=events.append,
        )
        recipe = {
            "schema_version": 1,
            "name": "Smoke",
            "variables": {"name": {"type": "string", "required": True}},
            "steps": [
                {"id": "open", "action": "navigate", "url": "https://example.test"},
                {
                    "id": "fill_name",
                    "action": "fill",
                    "selector": "#name",
                    "value": "{{name}}",
                },
            ],
            "output": {"type": "file"},
        }

        result = RecipeRunner().run(recipe, context)

        self.assertEqual(result.completed_steps, 2)
        self.assertEqual(result.failed_step_id, None)
        self.assertGreaterEqual(len(events), 2)


if __name__ == "__main__":
    unittest.main()
