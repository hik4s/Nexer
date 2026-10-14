import json
import os
import tempfile
from pathlib import Path
import unittest

from nexer_recorder.compiler import Recording
from nexer_recorder.scripts import recorder_script
from nexer_recorder.readiness import normalize_readiness
from playwright.sync_api import sync_playwright
from actions import create_default_registry
from context import ExecutionContext

def accept_capture(recording, event):
    wait, event = normalize_readiness(event, recording.steps[-1])
    if wait is not None:
        recording.accept(wait)
    recording.accept(event)


@unittest.skipUnless(os.getenv("NEXER_RUN_RECORDER_E2E") == "1", "Set NEXER_RUN_RECORDER_E2E=1 for synthetic Edge recording")
class EdgeCaptureTests(unittest.TestCase):
    def test_preparation_excludes_login_metadata_and_start_failure_recovers(self):
        events, starts, stopped = [], [], []
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(channel='msedge', headless=True)
            try:
                page = browser.new_page()
                page.expose_binding('nexerCapture', lambda source, event: events.append(event))
                page.expose_binding('nexerFinishRecording', lambda source: stopped.append(True))
                def start(source):
                    starts.append(True)
                    return {'started': len(starts) > 1, 'message': 'Abra a rota configurada.'}
                page.expose_binding('nexerStartRecording', start)
                page.set_content('<label>Login metadata canary<input id="company"></label><input type="password"><button id="login">Login</button>')
                page.evaluate('window.__nexerRecorderActive = false')
                page.evaluate(recorder_script())
                page.locator('#company').fill('preparation-canary')
                page.locator('input[type=password]').fill('password-canary')
                page.locator('#login').click()
                self.assertEqual(events, [])
                page.get_by_role('button', name='Iniciar gravação', exact=True).click()
                self.assertEqual(events, [])
                self.assertTrue(page.get_by_text('Abra a rota configurada.').is_visible())
                page.evaluate("document.querySelector('label').firstChild.textContent = 'Report field'")
                page.get_by_role('button', name='Iniciar gravação', exact=True).click()
                page.locator('#company').fill('recorded-canary')
                page.get_by_role('button', name='Parar gravação', exact=True).click()
                self.assertEqual(stopped, [True])
                self.assertEqual(len(events), 1)
                self.assertEqual(events[0]['label'], 'Report field')
                for canary in ('metadata canary', 'preparation-canary', 'password-canary', 'recorded-canary'):
                    self.assertNotIn(canary, json.dumps(events))
            finally:
                browser.close()

    def test_list_collection_matches_filename_without_download_button_caption(self):
        from actions import _matching_download
        recording = Recording('List report')
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(channel='msedge', headless=True)
            try:
                page = browser.new_page()
                page.expose_binding('nexerCapture', lambda source, event: accept_capture(recording, event))
                page.set_content('<ul><li>Relatorio_2026.csv<a download href="data:text/plain,test">Baixar</a></li></ul>')
                page.evaluate(recorder_script())
                page.locator('a').click()
                page.wait_for_timeout(100)
                collection = recording.recipe()['steps'][-1]['collection']
                self.assertIsNotNone(_matching_download(page, collection, 'Relatorio_*.csv'))
            finally:
                browser.close()
    def test_collection_download_replays_top_match_with_current_site_filename(self):
        with tempfile.TemporaryDirectory() as directory, sync_playwright() as playwright:
            browser = playwright.chromium.launch(channel="msedge", headless=True)
            try:
                page = browser.new_page(accept_downloads=True)
                page.set_content('''<table><tbody>
                  <tr><td>Outro_2026.csv</td><td><a download="Outro_2026.csv" href="data:text/plain,wrong">Baixar</a></td></tr>
                  <tr><td>Relatorio_2026.csv</td><td><a download="Relatorio_2026.csv" href="data:text/plain,newest">Baixar</a></td></tr>
                  <tr><td>Relatorio_2025.csv</td><td><a download="Relatorio_2025.csv" href="data:text/plain,older">Baixar</a></td></tr>
                </tbody></table>''')
                context = ExecutionContext(page=page, variables={'pattern': 'Relatorio_*.csv'}, downloads_dir=directory)
                step = {'id': 'download', 'selector': 'a', 'filename': 'download', 'preserve_filename': True,
                        'collection': {'rows': 'tbody > tr', 'name': 'td:first-child', 'button': 'a', 'pattern': '{{pattern}}'}}
                path = create_default_registry().execute('download', step, context)
                self.assertEqual(Path(path).name, 'Relatorio_2026.csv')
                self.assertEqual(Path(path).read_text(), 'newest')
                self.assertEqual(len(list(Path(directory).iterdir())), 1)
                context.variables['pattern'] = 'Missing_*.csv'
                context.resolver.values['pattern'] = 'Missing_*.csv'
                from actions import ActionExecutionError
                with self.assertRaisesRegex(ActionExecutionError, 'DOWNLOAD_MATCH_NOT_FOUND'):
                    create_default_registry().execute('download', {**step, 'timeout_ms': 1}, context)
                self.assertEqual(len(context.artifacts), 1)
            finally:
                browser.close()
    def test_labels_stop_toolbar_and_collection_do_not_capture_filled_values(self):
        recording = Recording("Report")
        stopped = []
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(channel="msedge", headless=True)
            try:
                page = browser.new_page()
                page.expose_binding("nexerCapture", lambda source, event: accept_capture(recording, event))
                page.expose_binding("nexerFinishRecording", lambda source: stopped.append(True))
                page.set_content('''<label>Data inicial <input type="date"></label>
                    <label for="company">Empresa</label><input id="company">
                    <table><tbody><tr><td>Recorded-file-canary.xlsx</td><td><a download href="data:text/plain,file">Baixar</a></td></tr></tbody></table>''')
                page.evaluate(recorder_script())
                self.assertEqual(set(recording.variables), {"base_url"})
                page.locator('input[type="date"]').fill("2031-02-17")
                page.locator('#company').fill("typed-company-canary")
                page.locator('a').click()
                page.wait_for_timeout(100)
                before = len(recording.steps)
                page.get_by_role('button', name='Parar gravação', exact=True).click()
                page.wait_for_timeout(100)
                self.assertEqual(stopped, [True])
                self.assertEqual(len(recording.steps), before)
                recipe = recording.recipe()
                self.assertEqual(recipe['variables']['input_001']['label'], 'Data inicial')
                self.assertEqual(recipe['variables']['company']['label'], 'Empresa')
                self.assertIn('collection', recipe['steps'][-1])
                for canary in ('2031-02-17', 'typed-company-canary', 'Recorded-file-canary.xlsx'):
                    self.assertNotIn(canary, json.dumps(recipe))
            finally:
                browser.close()
    def test_shadow_editing_double_click_hover_drag_and_scroll_replay(self):
        recording = Recording("Interactions")
        html = '''<html><body style="height:2400px"><section id="host"></section>
          <button id="counter" onclick="this.dataset.count=String(Number(this.dataset.count||0)+1)">Count</button>
          <button id="menu" aria-haspopup="menu" onpointerover="this.dataset.hovered='yes'">Menu</button>
          <div id="source" draggable="true">Drag</div><div id="destination" ondragover="event.preventDefault()" ondrop="this.dataset.dropped='yes';event.preventDefault()">Drop</div>
          </body></html>'''
        def shadow(page):
            page.evaluate("document.querySelector('#host').attachShadow({mode:'open'}).innerHTML='<input id=company>'")
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(channel="msedge", headless=True)
            try:
                context = browser.new_context()
                context.expose_binding("nexerCapture", lambda source, event: accept_capture(recording, event))
                page = context.new_page()
                page.set_content(html)
                shadow(page)
                page.evaluate(recorder_script())
                page.locator("#company").fill("shadow-company-canary")
                page.locator("#counter").dblclick()
                page.locator("#menu").hover()
                page.wait_for_timeout(300)
                page.locator("#source").drag_to(page.locator("#destination"))
                page.evaluate("window.scrollTo(0, 800)")
                page.wait_for_timeout(200)
                recipe = recording.recipe()
                self.assertNotIn("shadow-company-canary", json.dumps(recipe))
                for action in ("fill", "click", "hover", "drag", "scroll"):
                    self.assertIn(action, [step["action"] for step in recipe["steps"]])
                self.assertEqual(next(step for step in recipe["steps"] if step["action"] == "click")["click_count"], 2)
                replay = browser.new_context().new_page()
                replay.set_content(html)
                shadow(replay)
                execution = ExecutionContext(page=replay, variables={"company": "New shadow company"}, downloads_dir="temp")
                registry = create_default_registry()
                for step in recipe["steps"][1:]:
                    registry.execute(step["action"], step, execution)
                self.assertEqual(replay.locator("#company").input_value(), "New shadow company")
                self.assertEqual(replay.locator("#counter").get_attribute("data-count"), "2")
                self.assertEqual(replay.locator("#menu").get_attribute("data-hovered"), "yes")
                self.assertEqual(replay.locator("#destination").get_attribute("data-dropped"), "yes")
                self.assertEqual(replay.evaluate("window.scrollY"), 800)
            finally:
                browser.close()

    def test_real_dom_capture_exports_locations_and_parameters_without_values(self):
        events = []
        recording = Recording("Synthetic recorder")
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(channel="msedge", headless=True)
            context = browser.new_context(accept_downloads=False, service_workers="block")
            def accept(source, event):
                events.append(event)
                recording.accept(event)
            context.expose_binding("nexerCapture", accept)
            page = context.new_page()
            page.set_content('''<html><body>
                <input id="period_start" type="date" min="2020-01-01" max="2040-12-31" step="2"><input id="period_end" type="date">
                <textarea id="synthetic-secret-in-id"></textarea>
                <textarea id="comments"></textarea>
                <select id="regional"><option value="synthetic-option-canary">Synthetic label</option></select>
                <form><input name="username"><input type="password"><button id="login">Login</button></form>
                <button id="export">Export</button>
                </body></html>''')
            page.evaluate(recorder_script())
            page.locator("#period_start").fill("2031-02-17")
            page.locator("#period_end").fill("2031-03-29")
            page.locator("#comments").fill("synthetic-text-canary")
            page.locator("#regional").select_option("synthetic-option-canary")
            page.locator('[name="username"]').fill("synthetic-user-canary")
            page.locator('[type="password"]').fill("synthetic-password-canary")
            page.locator("#export").click()
            page.wait_for_timeout(100)
            self.assertEqual(recording.recipe()["variables"]["period_start"]["field"], {"control": "date", "required": False, "min": "2020-01-01", "max": "2040-12-31", "step": 2})
            serialized = json.dumps({"events": events, "recipe": recording.recipe()})
            for canary in ("2031-02-17", "2031-03-29", "synthetic-text-canary", "synthetic-option-canary",
                           "synthetic-user-canary", "synthetic-password-canary"):
                self.assertNotIn(canary, serialized)
            parameters = recording.recipe()["variables"]
            self.assertIn("period_start", parameters)
            self.assertIn("period_end", parameters)
            self.assertIn("regional", parameters)
            self.assertEqual([event["action"] for event in events], ["fill", "fill", "fill", "select", "click"])
            for event in events:
                self.assertEqual(page.locator(event["selector"]).count(), 1)
            context.close()
            browser.close()

    def test_enter_and_native_controls_are_recorded_once_and_frames_are_captured(self):
        events = []
        recording = Recording("Contexts")
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(channel="msedge", headless=True)
            try:
                context = browser.new_context()
                def accept(source, event):
                    events.append(event)
                    recording.accept({**event, **({"frames": ["iframe"]} if source["frame"].parent_frame else {})})
                context.expose_binding("nexerCapture", accept)
                context.add_init_script(script=recorder_script())
                page = context.new_page()
                page.set_content('''<form onsubmit="event.preventDefault()"><input id="field">
                  <input type="submit"><input type="checkbox"><input type="radio"></form>
                  <iframe srcdoc="<button>Nested</button>"></iframe>''')
                page.evaluate("delete window.__nexerRecorderInstalled")
                page.evaluate("delete window.__nexerRecorderDocument")
                page.evaluate(recorder_script())
                page.locator("#field").press("Enter")
                page.wait_for_timeout(100)
                self.assertEqual([event["action"] for event in events], ["press"])
                page.locator('[type="submit"]').click()
                page.locator('[type="checkbox"]').click()
                page.locator('[type="radio"]').click()
                page.frame_locator("iframe").locator("button").click()
                page.wait_for_timeout(100)
                self.assertEqual([step["action"] for step in recording.recipe()["steps"]], ["navigate", "press", "click", "check", "choose_radio", "click"])
                self.assertEqual(recording.recipe()["steps"][-1]["frames"], ["iframe"])
            finally:
                browser.close()
