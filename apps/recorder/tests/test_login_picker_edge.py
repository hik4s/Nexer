import json
import os
import unittest
from pathlib import Path
from playwright.sync_api import sync_playwright

@unittest.skipUnless(os.getenv("NEXER_RUN_RECORDER_E2E") == "1", "Synthetic Edge opt-in")
class LoginPickerEdgeTests(unittest.TestCase):
    def test_targets_are_captured_without_values_or_submission(self):
        script = Path(__file__).resolve().parents[1] / "nexer_recorder/login_capture.js"
        events = []
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(channel="msedge", headless=True)
            try:
                context = browser.new_context()
                context.expose_binding("nexerLoginTarget", lambda source, event: events.append(event))
                page = context.new_page()
                page.set_content('<form onsubmit="window.submitted=true;event.preventDefault()"><input value="user-canary"><input type=password value="password-canary"><button>Enter</button></form>')
                page.evaluate(script.read_text(encoding="utf-8"))
                page.locator('form input[type=text],form input:not([type])').click()
                page.locator('input[type=password]').click()
                page.locator('form button').click()
                page.wait_for_timeout(100)
                self.assertEqual([event["field"] for event in events], ["username_target", "password_target", "submit_target"])
                self.assertFalse(page.evaluate("Boolean(window.submitted)"))
                serialized = json.dumps(events)
                self.assertNotIn("user-canary", serialized); self.assertNotIn("password-canary", serialized)
                self.assertTrue(all(set(event) == {"field", "selector", "frames"} for event in events))
            finally: browser.close()
