from copy import deepcopy
import json
import tempfile
import unittest

from context import ExecutionContext
from recipe import validate_recipe, RecipeValidationError
from runner import RecipeRunner
from actions import ActionRegistry


def generation_recipe():
    collection = {'container': '#table', 'rows': '#table tr', 'name': '.name', 'button': 'a', 'pattern': '{{pattern}}',
                  'identity_attribute': 'data-job-id', 'shared': True}
    return {'schema_version': 1, 'name': 'Correlated download', 'variables': {'pattern': {'type': 'string'}},
            'steps': [
                {'id': 'base', 'action': 'snapshot_downloads', 'collection': deepcopy(collection)},
                {'id': 'request', 'action': 'request_download', 'selector': '#export', 'baseline': 'base',
                 'confirmation': {'selector': '#confirmation', 'attribute': 'data-job-id'}, 'timeout_ms': 180000},
                {'id': 'obtain', 'action': 'download', 'selector': 'a', 'generation': 'request',
                 'collection': deepcopy(collection), 'filename': 'download', 'preserve_filename': True, 'timeout_ms': 180000}],
            'output': {'type': 'file'}}


class GenerationContractTests(unittest.TestCase):
    def test_valid_contract_is_parameterized_and_does_not_mutate_recipe(self):
        recipe = generation_recipe()
        before = deepcopy(recipe)
        result = validate_recipe(recipe)
        self.assertEqual(result, before)
        self.assertEqual(recipe, before)
        self.assertNotIn('job-private-canary', json.dumps(result))

    def test_reference_retry_context_or_collection_mismatches_are_rejected(self):
        mutations = [
            lambda steps: steps[1].update(baseline='missing'),
            lambda steps: steps[2].update(generation='missing'),
            lambda steps: steps[1].update(retry={'max_attempts': 2}),
            lambda steps: steps[2].update(retry={'max_attempts': 2}),
            lambda steps: steps[1].update(frames=['iframe']),
            lambda steps: steps[2]['collection'].update(rows='other'),
            lambda steps: steps[1]['confirmation'].update(attribute='value'),
            lambda steps: steps[1]['confirmation'].update(secret='canary'),
            lambda steps: steps[1].update(button='right'),
            lambda steps: steps[1].update(click_count=True),
            lambda steps: steps[0]['collection'].pop('container'),
            lambda steps: steps[2].update(collection=None),
            lambda steps: steps[2].update(timeout_ms=900001),
            lambda steps: steps.insert(2, {'id': 'tab', 'action': 'switch_tab', 'index': 1}),
            lambda steps: steps.insert(1, {'id': 'extra', 'action': 'click', 'selector': '#other'}),
        ]
        for mutate in mutations:
            recipe = generation_recipe()
            mutate(recipe['steps'])
            with self.subTest(recipe=recipe), self.assertRaises(RecipeValidationError):
                validate_recipe(recipe)
        recipe = generation_recipe()
        recipe['steps'][0], recipe['steps'][1] = recipe['steps'][1], recipe['steps'][0]
        with self.assertRaises(RecipeValidationError):
            validate_recipe(recipe)

    def test_shared_collection_needs_correlation_but_old_recipes_remain_valid(self):
        recipe = generation_recipe()
        recipe['steps'] = [recipe['steps'][-1]]
        del recipe['steps'][0]['generation']
        with self.assertRaises(RecipeValidationError):
            validate_recipe(recipe)
        recipe['steps'][0]['collection'].pop('shared')
        recipe['steps'][0]['collection'].pop('identity_attribute')
        recipe['steps'][0]['collection'].pop('container')
        recipe['steps'][0]['timeout_ms'] = 30000
        validate_recipe(recipe)

    def test_memory_is_not_repr_or_reused_after_error_cancel_or_success(self):
        registry = ActionRegistry()
        def fill_state(step, context):
            context.download_state['private'] = 'job-private-canary'
            if step.get('fail'):
                raise RuntimeError('safe-error')
        registry.register('click', fill_state)
        with tempfile.TemporaryDirectory() as directory:
            context = ExecutionContext(page=None, variables={}, downloads_dir=directory)
            context.download_state['private'] = 'job-private-canary'
            self.assertNotIn('job-private-canary', repr(context))
            recipe = {'schema_version': 1, 'name': 'Memory', 'variables': {},
                      'steps': [{'id': 'one', 'action': 'click', 'selector': '#run'}], 'output': {'type': 'none'}}
            runner = RecipeRunner(registry)
            runner.run(recipe, context)
            self.assertEqual(context.download_state, {})
            recipe['steps'][0]['fail'] = True
            runner.run(recipe, context)
            self.assertEqual(context.download_state, {})
            context.download_state['private'] = 'job-private-canary'
            context.cancellation_requested = lambda: True
            self.assertTrue(runner.run(recipe, context).cancelled)
            self.assertEqual(context.download_state, {})
            context.download_state['private'] = 'job-private-canary'
            with self.assertRaises(RecipeValidationError):
                runner.run({}, context)
            self.assertEqual(context.download_state, {})


if __name__ == '__main__':
    unittest.main()
