import unittest


from context import ExecutionContext
from runner import RecipeRunner


class FakePage:
    def locator(self, selector):
        return self

    def click(self, **kwargs):
        pass

    def fill(self, value, **kwargs):
        pass

    def goto(self, url, wait_until="domcontentloaded", timeout=30000):
        pass


class RunnerTests(unittest.TestCase):
    def test_runner_executes_steps_in_order_and_emits_events(self):
        events = []
        context = ExecutionContext(
            page=FakePage(),
            variables={"name": "Kauan"},
            downloads_dir=__import__("tempfile").mkdtemp(),
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

    def test_runner_retries_a_step_when_explicitly_configured(self):
        events = []

        class FlakyPage:
            attempts = 0

            def locator(self, selector):
                return self

            def click(self, **kwargs):
                self.attempts += 1
                if self.attempts == 1:
                    raise RuntimeError("temporary")

        context = ExecutionContext(
            page=FlakyPage(),
            variables={},
            downloads_dir=__import__("tempfile").mkdtemp(),
            emit=events.append,
        )
        recipe = {
            "schema_version": 1,
            "name": "Retry",
            "variables": {},
            "steps": [
                {
                    "id": "click_once",
                    "action": "click",
                    "selector": "#ready",
                    "retry": {"max_attempts": 2, "backoff_ms": 0},
                }
            ],
            "output": {"type": "file"},
        }

        result = RecipeRunner().run(recipe, context)

        self.assertEqual(result.completed_steps, 1)
        self.assertIsNone(result.failed_step_id)
        self.assertIn("step.retrying", [event["type"] for event in events])

    def test_runner_stops_after_retry_limit(self):
        class AlwaysFailPage:
            attempts = 0

            def locator(self, selector):
                return self

            def click(self, **kwargs):
                self.attempts += 1
                raise RuntimeError("persistent")

        page = AlwaysFailPage()
        context = ExecutionContext(
            page=page,
            variables={},
            downloads_dir=__import__("tempfile").mkdtemp(),
        )
        recipe = {
            "schema_version": 1,
            "name": "Retry limit",
            "variables": {},
            "steps": [
                {
                    "id": "click",
                    "action": "click",
                    "selector": "#ready",
                    "retry": {"max_attempts": 3, "backoff_ms": 0},
                }
            ],
            "output": {"type": "file"},
        }

        result = RecipeRunner().run(recipe, context)

        self.assertEqual(page.attempts, 3)
        self.assertEqual(result.completed_steps, 0)
        self.assertEqual(result.failed_step_id, "click")
        self.assertFalse(result.cancelled)


if __name__ == "__main__":
    unittest.main()
