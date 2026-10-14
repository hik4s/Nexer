import json
import os
import tempfile
import unittest
from pathlib import Path

from playwright.sync_api import sync_playwright
from nexer_recorder.scripts import recorder_script
from nexer_recorder.compiler import Recording
from nexer_recorder.readiness import normalize_readiness
from actions import create_default_registry
from context import ExecutionContext

def accept_capture(recording, event):
    wait, event = normalize_readiness(event, recording.steps[-1])
    if wait is not None:
        recording.accept(wait)
    recording.accept(event)


@unittest.skipUnless(os.getenv('NEXER_RUN_RECORDER_E2E') == '1', 'Synthetic Edge selector tests')
class SelectorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.playwright = sync_playwright().start()
        cls.browser = cls.playwright.chromium.launch(channel='msedge', headless=True)

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.playwright.stop()

    def setUp(self):
        self.context = self.browser.new_context()
        self.addCleanup(self.context.close)
        self.page = self.context.new_page()

    def install(self):
        self.page.evaluate(recorder_script())

    def test_recorded_target_survives_inserted_sibling(self):
        recording = Recording('Stable task')
        self.page.expose_binding('nexerCapture', lambda source, event: accept_capture(recording, event))
        self.page.set_content('<input id="search"><button id="run" onclick="window.runs=(window.runs||0)+1">Run</button>')
        self.install()
        self.page.locator('#search').fill('typed-canary')
        self.page.locator('#run').click()
        recipe = recording.recipe()
        self.assertNotIn('typed-canary', json.dumps(recipe))
        self.page.evaluate("""() => {
            window.runs=0; window.decoyRuns=0;
            const input=document.createElement('input'); input.id='decoy'; document.querySelector('#search').before(input);
            const button=document.createElement('button'); button.textContent='Decoy'; button.onclick=()=>window.decoyRuns++;
            document.querySelector('#run').before(button);
        }""")
        with tempfile.TemporaryDirectory() as directory:
            context = ExecutionContext(page=self.page, variables={'input_001': 'new-input'}, downloads_dir=directory)
            for step in recipe['steps'][1:]:
                create_default_registry().execute(step['action'], step, context)
        self.assertEqual(self.page.locator('#search').input_value(), 'new-input')
        self.assertEqual(self.page.locator('#decoy').input_value(), '')
        self.assertEqual(self.page.evaluate('window.runs'), 1)
        self.assertEqual(self.page.evaluate('window.decoyRuns'), 0)

    def test_unsafe_or_duplicate_identifiers_are_not_promoted(self):
        self.page.set_content('<input id="search"><input id="search"><button id="private-canary-7391" name="secret-token" data-testid="record-7391">Go</button>')
        self.install()
        for index in range(2):
            selector = self.page.locator('input').nth(index).evaluate('el => window.__nexerSelectors.forElement(el)')
            self.assertEqual(self.page.locator(selector).count(), 1)
            self.assertTrue(self.page.locator(selector).evaluate('(el, index) => el === document.querySelectorAll("input")[index]', index))
        selector = self.page.locator('button').evaluate('el => window.__nexerSelectors.forElement(el)')
        for canary in ('private-canary', 'secret-token', 'record-7391'):
            self.assertNotIn(canary, selector)
        self.assertEqual(self.page.locator(selector).count(), 1)

    def test_relative_download_button_matches_each_row(self):
        recording = Recording('Collection')
        self.page.expose_binding('nexerCapture', lambda source, event: accept_capture(recording, event))
        self.page.set_content('<table id="table"><tbody><tr><td>File canary</td><td><button id="download" type="button">Baixar</button></td></tr><tr><td>Other</td><td><button type="button">Baixar</button></td></tr></tbody></table>')
        self.install()
        self.page.locator('#download').click()
        collection = recording.recipe()['steps'][-1]['collection']
        self.assertNotIn('File canary', json.dumps(collection))
        rows = self.page.locator(collection['rows'])
        self.assertEqual(rows.count(), 2)
        for index in range(2):
            self.assertEqual(rows.nth(index).locator(collection['button']).count(), 1)

    def test_shadow_host_and_frame_target_survive_layout_change(self):
        self.page.set_content('<section id="host"></section><iframe id="frame" srcdoc="<input id=search>"></iframe>')
        self.page.evaluate("document.querySelector('#host').attachShadow({mode:'open'}).innerHTML='<input id=search>'")
        self.install()
        selector = self.page.locator('#host input').evaluate('el => window.__nexerSelectors.forElement(el)')
        frame_selector = self.page.locator('iframe').evaluate('el => window.__nexerSelectors.forElement(el)')
        self.page.evaluate("""() => {
            const host=document.createElement('section'); host.attachShadow({mode:'open'}).innerHTML='<input>';
            document.querySelector('#host').before(host);
            const frame=document.createElement('iframe'); document.querySelector('#frame').before(frame);
            document.querySelector('#host').shadowRoot.querySelector('input').before(document.createElement('input'));
        }""")
        self.page.locator(selector).fill('right-shadow')
        self.page.frame_locator(frame_selector).locator('#search').fill('right-frame')
        self.assertEqual(self.page.locator('#host input#search').input_value(), 'right-shadow')
        self.assertEqual(self.page.frame_locator('#frame').locator('#search').input_value(), 'right-frame')

    def test_selector_policy_never_reads_input_value(self):
        self.page.set_content('<input id="private-record-7391" type="search" value="value-canary">')
        self.install()
        selector = self.page.locator('input').evaluate("""el => {
            Object.defineProperty(el, 'value', {get(){throw new Error('VALUE_READ');}});
            return window.__nexerSelectors.forElement(el);
        }""")
        self.assertNotIn('private-record', selector)
        self.assertNotIn('value-canary', selector)
        self.assertEqual(self.page.locator(selector).count(), 1)

    def test_light_and_shadow_names_are_not_ambiguous(self):
        self.page.set_content('<main><input id=search></main><section id=host></section>')
        self.page.evaluate("document.querySelector('#host').attachShadow({mode:'open'}).innerHTML='<input id=search>'")
        self.install()
        selector = self.page.locator('main input').evaluate('el => window.__nexerSelectors.forElement(el)')
        self.assertEqual(self.page.locator(selector).count(), 1)
        self.page.locator(selector).fill('right-input')
        self.assertEqual(self.page.locator('main input').input_value(), 'right-input')
        self.assertEqual(self.page.locator('#host input').input_value(), '')

    def test_cross_root_positional_collision_is_rejected(self):
        self.page.set_content('<div><input></div>')
        self.page.evaluate("document.querySelector('div').attachShadow({mode:'open'}).innerHTML='<input>'")
        self.install()
        selector = self.page.evaluate('window.__nexerSelectors.forElement(document.querySelector("input"))')
        self.assertIsNone(selector)


if __name__ == '__main__':
    unittest.main()
