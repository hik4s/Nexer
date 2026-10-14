from copy import deepcopy
import unittest

from recipe import validate_recipe, RecipeValidationError


def query_recipe():
    return {'schema_version': 1, 'name': 'Query', 'variables': {}, 'output': {'type': 'none'},
            'steps': [{'id': 'query', 'action': 'query', 'selector': '#search', 'frames': [],
                       'timeout_ms': 1000,
                       'confirmation': {'selector': '#confirmation', 'attribute': 'data-query-id'},
                       'result': {'container': '#result', 'attribute': 'data-query-id',
                                  'outcomes': {'data': '.data', 'empty': '.empty', 'error': '.error'}}}]}


class QueryRecipeTests(unittest.TestCase):
    def test_valid_contract_preserves_fields_without_mutating(self):
        recipe = query_recipe()
        before = deepcopy(recipe)
        self.assertEqual(validate_recipe(recipe), before)
        self.assertEqual(recipe, before)
        for timeout in (1000, 900000):
            recipe['steps'][0]['timeout_ms'] = timeout
            for attribute in ('data-query-id', 'data-request-id'):
                recipe['steps'][0]['confirmation']['attribute'] = attribute
                self.assertEqual(validate_recipe(recipe)['steps'][0]['action'], 'query')

    def test_invalid_contract_is_rejected(self):
        mutations = [(lambda s, v=v: s.update(timeout_ms=v)) for v in (999, 900001, True)]
        mutations += [
            lambda s: s.update(selector=' '), lambda s: s.update(selector='x' * 2049),
            lambda s: s.update(frames=['iframe'] * 17),
            lambda s: s.update(frames=['x' * 2049]),
            lambda s: s.update(retry={'max_attempts': 2}),
            lambda s: s['confirmation'].update(attribute='value'),
            lambda s: s['confirmation'].update(extra='secret'),
            lambda s: s['result'].update(extra='secret'),
            lambda s: s['result']['outcomes'].pop('empty'),
            lambda s: s['result']['outcomes'].update(extra='.extra'),
            lambda s: s['result']['outcomes'].update(empty=' .data '),
            lambda s: s.update(button='right'), lambda s: s.update(click_count=2),
            lambda s: s.update(value='private'), lambda s: s.update(unknown=True),
        ]
        for mutate in mutations:
            recipe = query_recipe()
            mutate(recipe['steps'][0])
            with self.subTest(step=recipe['steps'][0]), self.assertRaises(RecipeValidationError):
                validate_recipe(recipe)

    def test_legacy_click_remains_valid(self):
        recipe = query_recipe()
        recipe['steps'] = [{'id': 'click', 'action': 'click', 'selector': '#search'}]
        self.assertEqual(validate_recipe(recipe), recipe)
