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


if __name__ == "__main__":
    unittest.main()
