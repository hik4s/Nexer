import unittest
from unittest.mock import Mock
from nexer_worker.processor import WorkerExecutionProcessor


class QueryErrorPolicyTests(unittest.TestCase):
    def test_only_exact_query_codes_are_exposed(self):
        processor = object.__new__(WorkerExecutionProcessor)
        processor._execution_cancel_requested = Mock(return_value=False)
        processor._update_item = Mock()
        processor._emit = Mock()
        codes = ['QUERY_BASELINE_UNAVAILABLE', 'QUERY_IDENTITY_INVALID', 'QUERY_CONFIRMATION_TIMEOUT',
                 'QUERY_RESULT_TIMEOUT', 'QUERY_CONTEXT_MISMATCH', 'QUERY_SUPERSEDED',
                 'QUERY_OUTCOME_AMBIGUOUS', 'QUERY_NO_DATA', 'QUERY_SITE_ERROR',
                 'QUERY_AUTHORIZATION_REVOKED', 'QUERY_EXECUTION_FAILED']
        for raw in codes + ['QUERY_NO_DATA:private-canary', '<p>private-canary</p>']:
            with self.subTest(raw=raw):
                processor._mark_failed(1, 2, error_type='RuntimeError', error_detail=raw)
                expected = raw if raw in codes else 'AUTOMATION_FAILED'
                self.assertEqual(processor._update_item.call_args.kwargs['error_detail'], expected)
                self.assertNotIn('private-canary', repr(processor._emit.call_args))
