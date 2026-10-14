import unittest
from unittest.mock import Mock
from nexer_worker.processor import WorkerExecutionProcessor

class DownloadErrorPolicyTests(unittest.TestCase):
    def test_only_exact_safe_codes_are_exposed(self):
        processor = object.__new__(WorkerExecutionProcessor)
        processor._execution_cancel_requested = Mock(return_value=False)
        processor._update_item = Mock()
        processor._emit = Mock()
        for raw, expected in [('DOWNLOAD_MATCH_AMBIGUOUS','DOWNLOAD_MATCH_AMBIGUOUS'),
                              ('DOWNLOAD_MATCH_AMBIGUOUS:secret-canary','AUTOMATION_FAILED'),
                              ('secret-canary','AUTOMATION_FAILED')]:
            processor._mark_failed(1,2,error_type='RuntimeError',error_detail=raw)
            self.assertEqual(processor._update_item.call_args.kwargs['error_detail'], expected)
