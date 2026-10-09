import unittest
from unittest.mock import Mock

from context import ExecutionContext
from runner import RecipeRunner


class AuthenticationAwarePage:
    def goto(self, url, **kwargs):
        pass


class RunnerAuthenticationTests(unittest.TestCase):
    def test_runner_checks_authentication_before_each_step(self):
        auth_guard = Mock()
        page = AuthenticationAwarePage()
        events = []

        context = ExecutionContext(
            page=page,
            variables={},
            downloads_dir=".",
            emit=events.append,
            auth_guard=auth_guard,
        )

        recipe = {
            "schema_version": 1,
            "name": "Auth",
            "variables": {},
            "steps": [
                {
                    "id": "open",
                    "action": "navigate",
                    "url": "https://example.test",
                },
            ],
            "output": {"type": "file"},
        }

        result = RecipeRunner().run(recipe, context)

        self.assertEqual(result.completed_steps, 1)
        auth_guard.ensure_authenticated.assert_called_once_with(page)



    def test_revocation_between_attempts_prevents_retry_action(self):
        class Page:
            attempts = 0
            def locator(self, selector):
                return self
            def click(self, **kwargs):
                self.attempts += 1
                raise RuntimeError("transient")
        page = Page()
        class Guard:
            def ensure_authenticated(self, current):
                if current.attempts:
                    raise RuntimeError("CORPORATE_CONTEXT_REVOKED")
                return current
        context = ExecutionContext(page=page, variables={}, downloads_dir=".", auth_guard=Guard())
        recipe = {"schema_version": 1, "name": "Revocation", "variables": {},
                  "steps": [{"id": "click", "action": "click", "selector": "#report",
                             "retry": {"max_attempts": 2, "backoff_ms": 0}}],
                  "output": {"type": "file"}}
        with self.assertRaisesRegex(RuntimeError, "^CORPORATE_CONTEXT_REVOKED$"):
            RecipeRunner().run(recipe, context)
        self.assertEqual(page.attempts, 1)


if __name__ == "__main__":
    unittest.main()
