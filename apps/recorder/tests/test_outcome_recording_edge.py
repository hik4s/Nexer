"""The semantic recorder only compiles observed, high-confidence transitions."""
import json
import os
import tempfile
import unittest
from pathlib import Path
from context import ExecutionContext
from runner import RecipeRunner
from playwright.sync_api import sync_playwright
from nexer_recorder.compiler import Recording
from nexer_recorder.scripts import recorder_script
from nexer_recorder.smart_waits import optimize_recipe
from nexer_recorder.readiness import normalize_readiness


class RecorderOutcomeContractTests(unittest.TestCase):
    def test_typed_outcome_is_inserted_after_causal_click(self):
        recording = Recording("Search")
        recording.accept({"action": "click", "selector": "#search"})
        previous = recording.steps[-1]["id"]
        recording.accept_outcome({"busy_selector": "#busy", "ready_selector": "#result",
                                  "ready_state": "enabled", "confidence": "high"})
        recording.accept({"action": "click", "selector": "#result"})
        steps = recording.recipe()["steps"]
        self.assertEqual([s["action"] for s in steps], ["navigate", "click", "wait_for_outcome", "click"])
        self.assertEqual(steps[2]["after_step_id"], previous)
        self.assertEqual(steps[2]["ready_selector"], "#result")
        self.assertEqual(optimize_recipe(optimize_recipe(recording.recipe())), optimize_recipe(recording.recipe()))
        self.assertEqual(sum(s["action"] == "wait_for_outcome" for s in optimize_recipe(recording.recipe())["steps"]), 1)

    def test_outcome_is_rejected_if_not_immediately_after_click(self):
        recording = Recording("Wrong")
        with self.assertRaisesRegex(ValueError, "RECORDER_OUTCOME_INVALID"):
            recording.accept_outcome({"busy_selector": "#x", "ready_selector": "#y", "ready_state": "enabled", "confidence": "high"})
        recording.accept({"action": "fill", "selector": "#x"})
        with self.assertRaisesRegex(ValueError, "RECORDER_OUTCOME_INVALID"):
            recording.accept_outcome({"busy_selector": "#x", "ready_selector": "#y", "ready_state": "enabled", "confidence": "high"})
        recording.accept({"action": "click", "selector": "#go"})
        for bad in [
            {"busy_selector": "#b", "ready_selector": "#r", "ready_state": "enabled", "confidence": "low"},
            {"busy_selector": "#b", "ready_selector": "#r", "ready_state": "enabled",
             "confidence": "high", "html": "private-canary"},
        ]:
            with self.subTest(bad=bad):
                with self.assertRaisesRegex(ValueError, "RECORDER_OUTCOME_INVALID"):
                    recording.accept_outcome(bad)


@unittest.skipUnless(os.getenv("NEXER_RUN_RECORDER_E2E") == "1", "Edge opt-in")
class RecorderOutcomeEdgeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.playwright = sync_playwright().start()
        cls.browser = cls.playwright.chromium.launch(channel="msedge", headless=True)

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.playwright.stop()

    def test_finishing_after_search_flushes_last_proven_outcome(self):
        page = self.browser.new_page()
        self.addCleanup(page.close)
        recording = Recording("Search terminal")
        errors, finished = [], []
        def capture(_source, event):
            try:
                data = dict(event)
                outcome = data.pop("preceding_outcome", None)
                if outcome: recording.accept_outcome(outcome)
                if data.get("action") == "outcome_end": return
                wait, data = normalize_readiness(data, recording.steps[-1])
                if wait: recording.accept(wait)
                recording.accept(data)
            except Exception as exc:
                errors.append(str(exc))
        page.expose_binding("nexerCapture", capture)
        page.expose_binding("nexerFinishRecording", lambda _source: finished.append(True))
        page.set_content('''<section id="report"><button id="search" onclick="
          busy.hidden=false;
          setTimeout(()=>{busy.hidden=true;result.disabled=false},60)">Pesquisar</button>
          <div id="busy" role="progressbar" hidden></div>
          <button id="result" disabled>Exportar</button></section>''')
        page.evaluate(recorder_script())
        page.locator("#search").click()
        page.wait_for_timeout(150)
        page.get_by_role("button", name="Parar gravação").click()
        page.wait_for_function("window.__nexerRecorderController.signal.aborted")
        self.assertTrue(finished)
        self.assertFalse(errors, errors)
        self.assertEqual([s["action"] for s in recording.steps],
                         ["navigate", "click", "wait_for_outcome"])
        self.assertNotIn("Pesquisar", json.dumps(recording.recipe()))

    def test_recorded_search_outcome_executes_on_next_run(self):
        page = self.browser.new_page()
        self.addCleanup(page.close)
        recording = Recording("Portable results")
        errors = []
        def capture(_source, event):
            try:
                data = dict(event)
                prior = data.pop("preceding_outcome", None)
                if prior: recording.accept_outcome(prior)
                wait, data = normalize_readiness(data, recording.steps[-1])
                if wait: recording.accept(wait)
                recording.accept(data)
            except Exception as exc:
                errors.append(str(exc))
        page.expose_binding("nexerCapture", capture)
        html = """<section id="report"><button id="search" onclick="
          document.querySelector('#busy').hidden=false;
          setTimeout(()=>{
            document.querySelector('#busy').hidden=true;
            document.querySelector('#result').disabled=false;
          },70)">Search</button>
          <div id="busy" role="progressbar" hidden></div>
          <button id="result" disabled>Export</button></section>"""
        page.set_content(html)
        page.evaluate(recorder_script())
        page.locator("#search").click()
        page.locator("#result").click(timeout=5000)
        page.wait_for_timeout(150)
        self.assertFalse(errors, errors)
        actual = recording.recipe()
        self.assertIn("wait_for_outcome", [step["action"] for step in actual["steps"]])
        replay = self.browser.new_page()
        self.addCleanup(replay.close)
        replay.set_content(html)
        with tempfile.TemporaryDirectory() as directory:
            flow = dict(actual)
            flow["steps"] = [step for step in actual["steps"] if step["action"] != "navigate"]
            result = RecipeRunner().run(flow, ExecutionContext(
                page=replay, variables={'base_url': 'http://localhost:1/'}, downloads_dir=Path(directory)))
        self.assertIsNone(result.failed_step_id, result.error)
        self.assertEqual(result.completed_steps, len(flow["steps"]))
        self.assertTrue(replay.locator("#result").is_enabled())

    def test_click_loading_result_generates_wait_without_business_text(self):
        page = self.browser.new_page()
        self.addCleanup(page.close)
        recording = Recording("Search")
        received = []
        errors = []
        def capture(_source, event):
            received.append(event)
            try:
                event = dict(event)
                outcome = event.pop("preceding_outcome", None)
                if outcome is not None:
                    recording.accept_outcome(outcome)
                wait, event = normalize_readiness(event, recording.steps[-1])
                if wait is not None:
                    recording.accept(wait)
                recording.accept(event)
            except Exception as exc:
                errors.append(repr(exc))
        page.expose_binding("nexerCapture", capture)
        page.set_content('''<section id="report"><button id="search" onclick="
          document.querySelector('#busy').hidden=false;
          setTimeout(() => {
            document.querySelector('#busy').hidden=true;
            document.querySelector('#result').disabled=false;
          },65)">Pesquisar</button>
          <div id="busy" role="progressbar" hidden></div>
          <button id="result" disabled>Exportar</button>
          <input id="secret" type=password value="private-value-canary"></section>''')
        page.evaluate(recorder_script())
        page.locator("#search").click()
        page.locator("#result").click(timeout=4000)
        page.wait_for_timeout(150)
        actions = [s["action"] for s in recording.steps]
        self.assertFalse(errors, errors)
        self.assertEqual(actions, ["navigate", "click", "wait_for_outcome", "click"], received)
        wait = recording.steps[2]
        self.assertEqual(wait["after_step_id"], recording.steps[1]["id"])
        self.assertEqual(wait["ready_state"], "enabled")
        self.assertIn("busy_selector", wait)
        self.assertNotIn("private-value-canary", json.dumps(recording.recipe()))


if __name__ == "__main__":
    unittest.main()
