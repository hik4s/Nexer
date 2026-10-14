import tempfile
import unittest

from actions import create_default_registry
from context import ExecutionContext
from runner import RecipeRunner
from test_query_recipe import query_recipe


class QueryRunnerTests(unittest.TestCase):
    def test_dry_run_has_no_browser_access_or_outcome_claim(self):
        with tempfile.TemporaryDirectory() as directory:
            events = []
            context = ExecutionContext(object(), {}, directory, dry_run=True, emit=events.append)
            result = RecipeRunner().run(query_recipe(), context)
            self.assertIsNone(result.error)
            self.assertEqual(result.completed_steps, 1)
            self.assertNotIn('outcome', str(events))

    def test_empty_error_and_typed_cancel_stop_before_next_step(self):
        from query_execution import QueryExecutionError
        for code, cancelled in [('QUERY_NO_DATA', False), ('QUERY_SITE_ERROR', False), ('EXECUTION_CANCELLED', True)]:
            with self.subTest(code=code), tempfile.TemporaryDirectory() as directory:
                calls, events = [], []
                registry = create_default_registry()
                def fail(step, context):
                    raise QueryExecutionError(code)
                registry.register('query', fail)
                registry.register('click', lambda *args: calls.append('next'))
                recipe = query_recipe()
                recipe['steps'].append({'id': 'next', 'action': 'click', 'selector': '#next'})
                result = RecipeRunner(registry).run(recipe, ExecutionContext(object(), {}, directory, emit=events.append))
                self.assertEqual(calls, [])
                self.assertEqual(result.cancelled, cancelled)
                self.assertEqual(result.error, None if cancelled else code)
                self.assertIn('CANCELLED' if cancelled else 'FAILED', str(events))
