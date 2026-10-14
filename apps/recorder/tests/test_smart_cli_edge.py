"""Real CLI export/replay on a synthetic local site, with new values and layout."""
import contextlib
import importlib.util
import json
import os
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from playwright.sync_api import sync_playwright
from context import ExecutionContext
from runner import RecipeRunner

ROOT = Path(__file__).resolve().parents[3]


@unittest.skipUnless(os.getenv('NEXER_RUN_RECORDER_E2E') == '1', 'Synthetic smart recorder CLI')
class SmartCliTests(unittest.TestCase):
    def test_cli_records_readiness_and_replays_after_layout_change(self):
        self.record_and_replay(smart=True)

    def test_cli_without_smart_waits_keeps_observed_readiness(self):
        self.record_and_replay(smart=False)

    def record_and_replay(self, *, smart):
        html = '''<button id=run onclick="setTimeout(()=>{document.querySelector('#search').hidden=false;document.querySelector('#search').disabled=false}, window.delay||80)">Run</button>
            <input id=search disabled hidden>'''

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *_):
                pass

            def do_GET(self):
                self.send_response(200)
                self.send_header('Content-Type', 'text/html')
                self.end_headers()
                self.wfile.write(html.encode())

        server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(thread.join, 3)
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        url = f'http://127.0.0.1:{server.server_port}/'
        spec = importlib.util.spec_from_file_location('smart_record_cli', ROOT / 'scripts/record_recipe.py')
        recorder = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(recorder)
        with tempfile.TemporaryDirectory() as directory, sync_playwright() as playwright:
            def launch(**options):
                browser = playwright.chromium.launch(**{**options, 'headless': True})
                original_context = browser.new_context

                def new_context(**kwargs):
                    context = original_context(**kwargs)
                    original_page = context.new_page

                    def new_page():
                        page = original_page()
                        original_wait = page.wait_for_timeout
                        interacted = False

                        def interact(milliseconds):
                            nonlocal interacted
                            original_wait(milliseconds)
                            if interacted:
                                return
                            interacted = True
                            page.locator('#run').click()
                            page.locator('#search').fill('demonstration-canary')
                            original_wait(50)
                            page.get_by_role('button', name='Parar gravação', exact=True).click()

                        page.wait_for_timeout = interact
                        return page

                    context.new_page = new_page
                    return context

                browser.new_context = new_context
                return browser

            output = Path(directory) / 'recipe.json'
            args = ['record_recipe.py', '--url', url, '--output', str(output)] + (['--smart-waits'] if smart else [])
            runtime = SimpleNamespace(chromium=SimpleNamespace(launch=launch))
            with patch.object(recorder, 'sync_playwright', lambda: contextlib.nullcontext(runtime)), patch('sys.argv', args):
                recorder.main()
            recipe = json.loads(output.read_text(encoding='utf-8'))
            self.assertNotIn('demonstration-canary', json.dumps(recipe))
            waits = [step for step in recipe['steps'] if step['action'] == 'wait_for'
                     and step.get('learning', {}).get('confidence') == 'high']
            self.assertEqual(len(waits), 1)
            self.assertEqual(waits[0]['state'], 'enabled')
            browser = playwright.chromium.launch(channel='msedge', headless=True)
            try:
                page = browser.new_page()
                page.goto(url)
                page.evaluate('''() => {
                    window.delay=240;
                    const decoy=document.createElement('input'); decoy.id='decoy';
                    document.querySelector('#search').before(decoy);
                }''')
                context = ExecutionContext(page=page, variables={'base_url': url, 'input_001': 'new-input'}, downloads_dir=directory)
                # The initial navigate was exercised when opening the local page.
                result = RecipeRunner().run({**recipe, 'steps': recipe['steps'][1:]}, context)
                self.assertIsNone(result.error)
                self.assertEqual(page.locator('#search').input_value(), 'new-input')
                self.assertEqual(page.locator('#decoy').input_value(), '')
            finally:
                browser.close()


if __name__ == '__main__':
    unittest.main()
