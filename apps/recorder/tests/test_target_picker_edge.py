import json
import os
import unittest
from playwright.sync_api import sync_playwright
from nexer_recorder.target_picker import target_script, validate_selection


@unittest.skipUnless(os.getenv('NEXER_RUN_RECORDER_E2E') == '1', 'Synthetic target-picker Edge')
class TargetPickerEdgeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.playwright = sync_playwright().start()
        cls.browser = cls.playwright.chromium.launch(channel='msedge', headless=True)

    @classmethod
    def tearDownClass(cls):
        cls.browser.close(); cls.playwright.stop()

    def setUp(self):
        self.context = self.browser.new_context()
        self.addCleanup(self.context.close)
        self.picks, self.commands = [], []
        self.context.expose_binding('nexerTargetState', lambda source: {'active': False, 'kind': 'element'})
        self.context.expose_binding('nexerTargetCommand', lambda source, command: self.commands.append(command))
        self.context.expose_binding('nexerTargetCandidate', lambda source, event: self.picks.append((source, event)))
        self.context.add_init_script(target_script())
        self.page = self.context.new_page()

    def install(self, body):
        self.page.route('http://127.0.0.1:12345/**', lambda r: r.fulfill(content_type='text/html', body=body))
        self.page.goto('http://127.0.0.1:12345/form')
        self.page.locator('[data-nexer-target-picker]').first.wait_for()

    def activate(self, kind='element'):
        self.page.evaluate('(kind)=>window.__nexerTargetPicker.setActive(true,kind)', kind)

    def test_selection_prevents_pointer_click_and_submit_handlers(self):
        self.install('''<form onsubmit="window.effects++"><button id="run">Run</button></form>
            <script>window.effects=0;window.addEventListener('pointerdown',()=>window.effects++,true);
            window.addEventListener('click',()=>window.effects++,true);</script>''')
        self.activate()
        self.page.locator('#run').click()
        self.page.wait_for_timeout(100)
        self.assertEqual(self.page.evaluate('effects'), 0)
        source, event = self.picks[0]
        self.assertEqual(validate_selection(source, event, self.page, 'element'), {'selector': '#run'})

    def test_values_labels_and_arbitrary_ids_are_not_collected(self):
        self.install('<label>private-canary<input id="private-canary" value="private-canary"></label>')
        self.activate('text')
        self.page.locator('input').click(); self.page.wait_for_timeout(60)
        source, event = self.picks[0]
        self.assertNotIn('private-canary', json.dumps(event))
        self.assertEqual(set(validate_selection(source, event, self.page, 'text')), {'selector'})

    def test_replaced_target_is_not_accepted_just_because_selector_still_matches(self):
        self.install('<button id="run">Run</button>'); self.activate()
        self.page.locator('#run').click(); self.page.wait_for_timeout(50)
        source,event=self.picks[0]
        self.page.locator('#run').evaluate('(n)=>n.replaceWith(n.cloneNode(true))')
        with self.assertRaises(ValueError): validate_selection(source,event,self.page,'element')

    def test_wrong_kind_password_and_child_frame_are_rejected(self):
        self.install('<button id="run">Run</button><input type="password"><iframe srcdoc="<button>Nested</button>"></iframe>')
        self.activate('text')
        self.page.locator('#run').click(); self.page.wait_for_timeout(50)
        with self.assertRaises(ValueError): validate_selection(*self.picks[0], self.page, 'text')
        self.page.evaluate("() => window.__nexerTargetPicker.setActive(true,'text')")
        self.page.locator('input').click(); self.page.wait_for_timeout(50)
        with self.assertRaises(ValueError): validate_selection(*self.picks[-1], self.page, 'text')
        self.page.evaluate("() => window.__nexerTargetPicker.setActive(true,'element')")
        self.page.frames[1].locator('button').click(); self.page.wait_for_timeout(50)
        with self.assertRaises(ValueError): validate_selection(*self.picks[-1], self.page, 'element')

    def test_preparation_allows_navigation_controls_but_toolbar_is_intercepted(self):
        self.install('<button id="run" onclick="window.effects++">Run</button><script>window.effects=0;</script>')
        self.page.locator('#run').click()
        self.assertEqual(self.page.evaluate('effects'), 1)
        self.assertEqual(self.picks, [])
        self.page.get_by_role('button', name='Selecionar alvo', exact=True).click()
        self.page.wait_for_timeout(50)
        self.assertEqual(self.commands, ['activate'])

    def test_open_shadow_target_is_structural_and_synthetic_click_is_ignored(self):
        self.install('<x-host></x-host><script>document.querySelector("x-host").attachShadow({mode:"open"}).innerHTML="<input type=text value=private-canary>"</script>')
        self.activate('text')
        self.page.locator('input').evaluate('(n)=>n.click()')
        self.page.wait_for_timeout(40); self.assertEqual(self.picks, [])
        self.page.locator('input').click(); self.page.wait_for_timeout(50)
        source, event = self.picks[0]
        self.assertNotIn('private-canary', json.dumps(event))
        self.assertEqual(validate_selection(source, event, self.page, 'text')['selector'], 'x-host input[type="text"]')
