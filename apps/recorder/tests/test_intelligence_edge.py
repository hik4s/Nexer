import json
import os
import unittest
from pathlib import Path

from playwright.sync_api import sync_playwright
from nexer_recorder.scripts import recorder_script



@unittest.skipUnless(os.getenv('NEXER_RUN_RECORDER_E2E') == '1', 'Synthetic Edge intelligence tests')
class IntelligenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.playwright = sync_playwright().start()
        cls.browser = cls.playwright.chromium.launch(channel='msedge', headless=True)

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.playwright.stop()

    def setUp(self):
        self.page = self.browser.new_page()
        self.addCleanup(self.page.close)
        self.events = []
        self.page.expose_binding('nexerCapture', lambda source, event: self.events.append(event))
        self.page.evaluate('''() => {
            const deliver=window.nexerCapture; window.delivered=0;
            window.nexerCapture=async event => {await deliver(event); window.delivered++;};
        }''')

    def install(self):
        self.page.evaluate(recorder_script())

    def delivered(self, count):
        self.page.wait_for_function('count => window.delivered >= count', arg=count)

    def test_sync_enable_and_parent_reveal_emit_readiness(self):
        self.page.set_content('''<button id=run onclick="document.querySelector('#search').disabled=false;document.querySelector('#panel').hidden=false">Run</button>
            <input id=search disabled><div id=panel hidden><button id=submit>Next</button></div>''')
        self.install()
        self.page.locator('#run').click()
        self.page.locator('#search').fill('typed-canary')
        self.delivered(2)
        self.assertEqual(self.events[-1].get('readiness'), {'state': 'enabled'})
        # A fresh reveal follows the last captured fill, not the earlier click.
        self.page.evaluate("document.querySelector('#panel').hidden=true")
        self.page.wait_for_timeout(10)
        self.page.evaluate("document.querySelector('#panel').hidden=false;document.querySelector('#submit').click()")
        self.page.wait_for_timeout(10)
        self.delivered(3)
        self.assertEqual(self.events[-1].get('readiness'), {'state': 'visible'})
        self.assertNotIn('typed-canary', json.dumps(self.events))

    def test_preparation_changes_are_reset_before_recording(self):
        self.page.set_content('<button id=run>Run</button><input id=search disabled>')
        self.page.evaluate('window.__nexerRecorderActive=false')
        self.install()
        self.page.evaluate("document.querySelector('#search').disabled=false")
        self.page.locator('#search').fill('preparation-canary')
        self.assertEqual(self.events, [])
        self.page.evaluate('window.__nexerRecorderActive=true; window.__nexerIntelligence.reset()')
        self.page.locator('#search').fill('recorded-canary')
        self.delivered(1)
        self.assertNotIn('readiness', self.events[-1])

    def test_reinstall_does_not_duplicate_capture(self):
        self.page.set_content('<button id=run onclick="document.querySelector(\'#search\').disabled=false">Run</button><input id=search disabled>')
        self.install()
        self.install()
        self.page.locator('#run').click()
        self.page.locator('#search').fill('new')
        self.page.wait_for_function('window.delivered === 2')
        self.assertEqual(len(self.events), 2, self.events)
        self.assertEqual(self.events[-1].get('readiness'), {'state': 'enabled'})
        self.page.evaluate('window.__nexerRecorderController.abort()')
        self.page.locator('#run').click()
        self.assertEqual(len(self.events), 2)

    def test_expired_and_actionless_changes_emit_no_readiness(self):
        self.page.set_content('<button id=run>Run</button><input id=search disabled>')
        self.page.evaluate('window.clock=0; performance.now=()=>window.clock')
        self.install()
        self.page.evaluate("document.querySelector('#search').disabled=false")
        self.page.locator('#search').fill('first')
        self.delivered(1)
        self.assertNotIn('readiness', self.events[-1])
        self.page.evaluate("document.querySelector('#search').disabled=true")
        self.page.locator('#run').click()
        self.page.evaluate("document.querySelector('#search').disabled=false")
        self.page.wait_for_timeout(10)
        self.page.evaluate('window.clock=30001')
        self.page.locator('#search').fill('expired')
        self.delivered(3)
        self.assertNotIn('readiness', self.events[-1])

    def test_shadow_and_sensitive_contexts(self):
        self.page.set_content('<button id=run>Run</button><section id=host></section><form><input type=password><input id=secret-token disabled></form>')
        self.page.evaluate("document.querySelector('#host').attachShadow({mode:'open'}).innerHTML='<input id=search disabled>'")
        self.install()
        self.page.locator('#run').click()
        self.page.evaluate("document.querySelector('#host').shadowRoot.querySelector('input').disabled=false;document.querySelector('#secret-token').disabled=false")
        self.page.locator('#host input').fill('shadow-canary')
        self.delivered(2)
        self.assertEqual(self.events[-1].get('readiness'), {'state': 'enabled'})
        self.page.locator('#secret-token').fill('secret-canary')
        self.assertEqual(len(self.events), 2)
        self.assertNotIn('canary', json.dumps(self.events))

    def test_oversized_mutation_batch_omits_inference(self):
        self.page.set_content('<button id=run>Run</button><input id=search disabled>')
        self.install()
        self.page.locator('#run').click()
        self.page.evaluate("""() => {
            const fragment=document.createDocumentFragment();
            for(let i=0;i<260;i++) fragment.append(document.createElement('input'));
            document.body.append(fragment); document.querySelector('#search').disabled=false;
        }""")
        self.page.locator('#search').fill('safe')
        self.delivered(2)
        self.assertNotIn('readiness', self.events[-1])

    def test_cancelled_initialization_does_not_reset_new_recording(self):
        self.page.set_content('<button id=run onclick="document.querySelector(\'#search\').disabled=false">Run</button><input id=search disabled>')
        self.page.evaluate('() => {window.pending=[]; window.nexerRecordingState=()=>new Promise(resolve=>window.pending.push(resolve));}')
        self.install()
        self.install()
        self.page.evaluate('window.pending[1](true)')
        self.page.wait_for_function('window.__nexerRecorderInstalled === true')
        self.page.locator('#run').click()
        self.page.evaluate('window.pending[0](true)')
        self.page.locator('#search').fill('new')
        self.delivered(2)
        self.assertEqual(self.events[-1].get('readiness'), {'state': 'enabled'})

    def test_pause_immediately_invalidates_unconsumed_readiness(self):
        self.page.set_content('<button id=run>Run</button><input id=search disabled>')
        self.install()
        self.page.locator('#run').click()
        self.page.evaluate("document.querySelector('#search').disabled=false")
        self.page.wait_for_timeout(10)
        self.page.evaluate('window.__nexerRecorderActive=false;window.__nexerRecorderActive=true')
        self.page.locator('#search').fill('new')
        self.delivered(2)
        self.assertNotIn('readiness', self.events[-1])

    def test_late_inactive_response_does_not_pause_active_installation(self):
        self.page.set_content('<button id=run>Run</button>')
        self.page.evaluate('() => {window.pending=[]; window.nexerRecordingState=()=>new Promise(resolve=>window.pending.push(resolve));}')
        self.install()
        self.install()
        self.page.evaluate('window.pending[1](true)')
        self.page.wait_for_function('window.__nexerRecorderInstalled === true')
        self.page.evaluate('window.pending[0](false)')
        self.assertTrue(self.page.evaluate('window.__nexerRecorderActive === true'))
        self.page.locator('#run').click()
        self.delivered(1)

    def test_new_action_can_learn_after_oversized_batch(self):
        self.page.set_content('<button id=run>Run</button><input id=search disabled>')
        self.install()
        self.page.locator('#run').click()
        self.page.evaluate('''() => {
            const fragment=document.createDocumentFragment();
            for(let i=0;i<260;i++) fragment.append(document.createElement('input'));
            document.body.append(fragment);
        }''')
        self.page.wait_for_timeout(10)
        self.page.locator('#run').click()
        self.page.evaluate("document.querySelector('#search').disabled=false")
        self.page.locator('#search').fill('new')
        self.delivered(3)
        self.assertEqual(self.events[-1].get('readiness'), {'state': 'enabled'})


if __name__ == '__main__':
    unittest.main()
