"""Executable post-click outcomes must be race-safe, typed and non-repeating."""
import tempfile
import threading
import unittest
from pathlib import Path
from playwright.sync_api import sync_playwright

from context import ExecutionContext
from recipe import validate_recipe, RecipeValidationError
from runner import RecipeRunner


def recipe(*steps):
    return {"schema_version": 1, "name": "Outcome test", "variables": {},
            "steps": [{"id": "open", "action": "navigate", "url": "http://localhost:1/"}, *steps],
            "output": {"type": "none"}}


CLICK = {"id": "search", "action": "click", "selector": "#search"}
WAIT = {"id": "wait_search", "action": "wait_for_outcome", "after_step_id": "search",
        "busy_selector": "#busy", "ready_selector": "#result",
        "ready_state": "enabled", "timeout_ms": 1500,
        "learning": {"source": "automatic", "confidence": "high"}}


class OutcomeContractTests(unittest.TestCase):
    def test_correct_consecutive_click_and_wait(self):
        self.assertEqual(validate_recipe(recipe(CLICK, WAIT))["steps"][-1], WAIT)

    def test_reject_dangerous_contracts(self):
        invalid = [
            ({**WAIT, "after_step_id": "missing"}, "OUTCOME_PREDECESSOR_INVALID"),
            ({**WAIT, "after_step_id": "open"}, "OUTCOME_PREDECESSOR_INVALID"),
            ({**WAIT, "ready_selector": ""}, "OUTCOME_CONTRACT_INVALID"),
            ({**WAIT, "timeout_ms": 0}, "STEP_TIMEOUT_INVALID"),
            ({**WAIT, "retry": {"max_attempts": 2}}, "OUTCOME_RETRY_FORBIDDEN"),
            ({**WAIT, "learning": {"source": "automatic", "confidence": "low"}}, "WAIT_LEARNING_INVALID"),
            ({**WAIT, "script": "alert(1)"}, "OUTCOME_CONTRACT_INVALID"),
            ({**WAIT, "frames": ["iframe"]}, "OUTCOME_CONTRACT_INVALID"),
        ]
        for payload, reason in invalid:
            with self.subTest(payload=payload):
                with self.assertRaisesRegex(RecipeValidationError, reason):
                    validate_recipe(recipe(CLICK, payload))


class OutcomeEdgeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.playwright = sync_playwright().start()
        cls.browser = cls.playwright.chromium.launch(channel="msedge", headless=True)

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.playwright.stop()

    def run_steps(self, markup, *, wait=WAIT, cancellation=None):
        # Run a localhost-free synthetic recipe; navigate would overwrite the fixture.
        page = self.browser.new_page()
        self.addCleanup(page.close)
        page.set_content(markup)
        with tempfile.TemporaryDirectory() as directory:
            context = ExecutionContext(page=page, variables={}, downloads_dir=Path(directory),
                                       cancellation_requested=cancellation)
            return RecipeRunner().run({"schema_version": 1, "name": "Outcome",
                   "variables": {}, "steps": [CLICK, wait], "output": {"type": "none"}}, context)

    def test_fast_spinner_and_ready_transition_succeeds(self):
        result = self.run_steps("""<button id=search onclick="
              busy.hidden=false;result.disabled=true;
              setTimeout(()=>{busy.hidden=true;result.disabled=false},40)">Search</button>
              <div id=busy role=progressbar hidden></div><button id=result>Export</button>""")
        self.assertEqual(result.completed_steps, 2, result.error)
        self.assertIsNone(result.failed_step_id)

    def test_preexisting_result_and_no_loading_do_not_pass(self):
        result = self.run_steps('<button id=search>Search</button><button id=result>Old export</button><div id=busy hidden></div>',
                                wait={**WAIT, "timeout_ms": 250})
        self.assertEqual(result.failed_step_id, "wait_search")
        self.assertIn("OUTCOME_TIMEOUT", result.error)

    def test_spinner_vanishes_but_old_ready_stays_visible_is_not_success(self):
        result = self.run_steps("""<button id=search onclick="
              busy.hidden=false;setTimeout(()=>busy.hidden=true,40)">Search</button>
              <div id=busy role=progressbar hidden></div><button id=result>Old export</button>""",
              wait={**WAIT, "timeout_ms": 300})
        self.assertEqual(result.failed_step_id, "wait_search")
        self.assertIn("OUTCOME_TIMEOUT", result.error)

    def test_explicit_error_blocks_downstream_steps(self):
        result = self.run_steps("""<button id=search onclick="
              setTimeout(()=>error.hidden=false,30)">Search</button>
              <div id=busy hidden></div><button id=result disabled>Export</button>
              <div id=error role=alert hidden>Bad credentials</div>""",
              wait={**WAIT, "error_selector": "#error"})
        self.assertEqual(result.failed_step_id, "wait_search")
        self.assertIn("OUTCOME_ERROR_STATE", result.error)
        self.assertNotIn("Bad credentials", result.error)

    def test_cancellation_stops_wait_without_click_retry(self):
        event = threading.Event()
        # cancellation is called by poll loop, not only before click
        attempts = iter([False] * 3 + [True] * 50)
        result = self.run_steps('<button id=search>Search</button><div id=busy hidden></div><button id=result disabled>Export</button>',
                                cancellation=lambda: next(attempts, True))
        self.assertIsNone(result.failed_step_id)
        self.assertTrue(result.cancelled)
        self.assertIsNone(result.error)

    def test_busy_never_finishes(self):
        result = self.run_steps("""<button id=search onclick="busy.hidden=false">Search</button>
              <div id=busy role=progressbar hidden></div><button id=result disabled>Export</button>""",
              wait={**WAIT, "timeout_ms": 250})
        self.assertEqual(result.failed_step_id, "wait_search")
        self.assertIn("OUTCOME_TIMEOUT", result.error)


if __name__ == "__main__":
    unittest.main()
