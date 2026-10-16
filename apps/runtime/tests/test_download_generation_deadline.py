import unittest
from types import SimpleNamespace
from unittest.mock import patch

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from download_generation import DownloadGenerationError, _confirmation, _rows


class _TimedOutLocator:
    def count(self):
        return 1

    def is_visible(self):
        return True

    def get_attribute(self, *_args, **_kwargs):
        raise PlaywrightTimeoutError("Synthetic Playwright read deadline")

    def evaluate(self, *_args, **_kwargs):
        raise PlaywrightTimeoutError("Synthetic Playwright DOM evaluation deadline")


class _Scope:
    def locator(self, _selector):
        return _TimedOutLocator()


def _context():
    return SimpleNamespace(resolve=lambda value: value, is_cancellation_requested=lambda: False,
                           auth_guard=None, page=object())


class DeadlineClassificationTests(unittest.TestCase):
    def test_confirmation_read_at_expired_deadline_is_a_timeout_not_generic_failure(self):
        with patch("download_generation.monotonic", return_value=10.0):
            with self.assertRaisesRegex(DownloadGenerationError, "DOWNLOAD_CONFIRMATION_TIMEOUT"):
                _confirmation(_Scope(), {"selector": "#confirmation", "attribute": "data-job-id"},
                              _context(), 9.99)

    def test_old_confirmation_read_uncertain_cannot_be_treated_as_absent(self):
        with patch("download_generation.monotonic", return_value=10.0):
            with self.assertRaisesRegex(DownloadGenerationError, "DOWNLOAD_CONFIRMATION_TIMEOUT"):
                _confirmation(_Scope(), {"selector": "#confirmation", "attribute": "data-job-id"},
                              _context(), 10.5, require_visible=False)

    def test_current_confirmation_transient_read_does_not_end_request_early(self):
        with patch("download_generation.monotonic", return_value=10.0):
            self.assertIsNone(_confirmation(_Scope(),
                {"selector": "#confirmation", "attribute": "data-job-id"},
                _context(), 10.5))

    def test_collection_evaluate_timeout_has_specific_code_for_generation(self):
        with patch("download_generation.monotonic", return_value=10.0):
            with self.assertRaisesRegex(DownloadGenerationError, "DOWNLOAD_GENERATION_TIMEOUT"):
                _rows(_Scope(), {"container": "#table"}, 9.99, timeout_code="DOWNLOAD_GENERATION_TIMEOUT")


if __name__ == "__main__":
    unittest.main()
