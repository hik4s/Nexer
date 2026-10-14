import json
import os
from pathlib import Path
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from time import monotonic as clock
import unittest
from unittest.mock import patch

from playwright.sync_api import sync_playwright
from actions import create_default_registry
from context import ExecutionContext
from runner import RecipeRunner
from test_download_generation_recipe import generation_recipe


@unittest.skipUnless(os.getenv('NEXER_RUN_RECORDER_E2E') == '1', 'Synthetic correlated Edge downloads')
class GenerationEdgeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.playwright = sync_playwright().start()
        cls.browser = cls.playwright.chromium.launch(channel='msedge', headless=True)

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.playwright.stop()

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.page = self.browser.new_page(accept_downloads=True)
        self.addCleanup(self.page.close)
        self.events = []
        self.context = ExecutionContext(page=self.page, variables={'pattern': 'Report-*.csv'},
                                        downloads_dir=self.directory.name, emit=self.events.append)
        self.registry = create_default_registry()
        self.recipe = generation_recipe()
        self.page.set_content('''<button id=export>Generate</button><span style="display:inline-block;width:1px;height:1px" id=confirmation data-job-id=old></span>
            <table id=table><tbody><tr data-job-id=old><td class=name>Report-123.csv</td><td><a download="Report-123.csv" href="data:text/plain,old">Download</a></td></tr></tbody></table>''')

    def execute(self, index):
        step = self.recipe['steps'][index]
        self.context.current_step_id = step['id']
        return self.registry.execute(step['action'], step, self.context)

    def generate(self, *, delay=80, duplicate=False, filename=False):
        if filename:
            for step in (self.recipe['steps'][0], self.recipe['steps'][2]):
                step['collection'].pop('identity_attribute')
            self.recipe['steps'][1]['confirmation'].pop('attribute')
        self.page.evaluate('''({delay, duplicate, filename}) => {
            document.querySelector('#export').onclick=()=>{
                window.generated=(window.generated||0)+1;
                const key=filename?'Report-new.csv':'request-new';
                if(filename) document.querySelector('#confirmation').textContent=key;
                else document.querySelector('#confirmation').setAttribute('data-job-id',key);
                setTimeout(()=>{
                    const row=document.createElement('tr');row.setAttribute('data-job-id',key);
                    row.innerHTML='<td class=name>'+(filename?'Report-new.csv':'Report-123.csv')+'</td><td><a download="Report-123.csv" href="data:text/plain,new">Download</a></td>';
                    document.querySelector('tbody').prepend(row);
                    if(duplicate) document.querySelector('tbody').append(row.cloneNode(true));
                },delay);
            };
        }''', {'delay': delay, 'duplicate': duplicate, 'filename': filename})

    def test_delayed_new_job_with_same_filename_is_selected(self):
        self.generate(delay=2700)
        self.execute(0)
        self.execute(1)
        path = self.execute(2)
        self.assertEqual(Path(path).read_text(), 'new')
        self.assertEqual(self.page.evaluate('window.generated'), 1)
        self.assertNotIn('request-new', json.dumps(self.events))

    def test_full_filename_confirmation_also_correlates(self):
        self.generate(filename=True)
        self.execute(0)
        self.execute(1)
        self.assertEqual(Path(self.execute(2)).read_text(), 'new')

    def test_ambiguous_job_never_clicks_either_candidate(self):
        self.generate(duplicate=True)
        self.execute(0)
        self.execute(1)
        self.page.wait_for_timeout(120)
        with self.assertRaisesRegex(RuntimeError, 'DOWNLOAD_MATCH_AMBIGUOUS'):
            self.execute(2)
        self.assertEqual(list(Path(self.directory.name).iterdir()), [])

    def test_stale_or_duplicate_confirmation_does_not_resubmit(self):
        self.page.evaluate("() => { document.querySelector('#export').onclick=()=>{window.generated=(window.generated||0)+1;}; }")
        self.execute(0)
        with patch('download_generation.monotonic', lambda: clock() * 1000):
            with self.assertRaisesRegex(RuntimeError, 'DOWNLOAD_CONFIRMATION_TIMEOUT'):
                self.execute(1)
        self.assertEqual(self.page.evaluate('window.generated'), 1)
        self.page.evaluate("document.body.append(document.querySelector('#confirmation').cloneNode(true))")
        with self.assertRaisesRegex(RuntimeError, 'DOWNLOAD_CONFIRMATION_AMBIGUOUS'):
            self.execute(1)
        self.assertEqual(self.page.evaluate('window.generated'), 1)

    def test_hidden_old_confirmation_is_not_a_new_request(self):
        self.page.evaluate("() => { const marker=document.querySelector('#confirmation'); marker.style.display='none'; marker.setAttribute('data-job-id','older-job'); document.querySelector('#export').onclick=()=>{marker.style.display='inline-block';}; }")
        self.execute(0)
        with patch('download_generation.monotonic', lambda: clock() * 100):
            with self.assertRaisesRegex(RuntimeError, 'DOWNLOAD_CONFIRMATION_TIMEOUT'):
                self.execute(1)
        self.assertNotIn('request', self.context.download_state)

    def test_cancel_while_trigger_disabled_does_not_generate_later(self):
        self.page.evaluate("() => { const button=document.querySelector('#export'); button.disabled=true; button.onclick=()=>{window.generated=(window.generated||0)+1;}; setTimeout(()=>{button.disabled=false;},500); }")
        self.execute(0)
        started = clock()
        self.context.cancellation_requested = lambda: clock() - started > .15
        with self.assertRaisesRegex(RuntimeError, 'EXECUTION_CANCELLED'):
            self.execute(1)
        self.page.wait_for_timeout(550)
        self.assertEqual(self.page.evaluate('window.generated || 0'), 0)

    def test_revocation_while_trigger_disabled_does_not_generate_later(self):
        self.page.evaluate("() => { const button=document.querySelector('#export'); button.disabled=true; button.onclick=()=>{window.generated=1;}; setTimeout(()=>{button.disabled=false;},500); }")
        self.execute(0)
        started = clock()
        class Guard:
            def ensure_authenticated(self, page):
                if clock() - started > .15:
                    raise RuntimeError('private-auth-canary')
                return page
        self.context.auth_guard = Guard()
        with self.assertRaisesRegex(RuntimeError, 'DOWNLOAD_AUTHORIZATION_REVOKED'):
            self.execute(1)
        self.page.wait_for_timeout(550)
        self.assertEqual(self.page.evaluate('window.generated || 0'), 0)

    def test_cancel_while_waiting_for_download_event_does_not_save(self):
        self.generate()
        self.execute(0)
        self.execute(1)
        self.page.wait_for_timeout(120)
        self.page.evaluate("() => { const link=document.querySelector('tr[data-job-id=request-new] a'); link.removeAttribute('href'); }")
        started = clock()
        self.context.cancellation_requested = lambda: clock() - started > .2
        with self.assertRaisesRegex(RuntimeError, 'EXECUTION_CANCELLED'):
            self.execute(2)
        self.assertEqual(self.context.artifacts, [])

    def test_removed_root_does_not_wait_for_late_reappearance_and_click(self):
        import download_generation
        self.generate()
        self.execute(0)
        self.execute(1)
        self.page.wait_for_timeout(120)
        original = download_generation._rows
        def disappear(*args):
            items = original(*args)
            self.page.evaluate("() => { const root=document.querySelector('#table'); root.remove(); setTimeout(()=>document.body.append(root),700); }")
            return items
        started = clock()
        with patch('download_generation._rows', disappear):
            with self.assertRaisesRegex(RuntimeError, 'DOWNLOAD_GENERATION_FAILED'):
                self.execute(2)
        self.assertLess(clock() - started, 1.5)
        self.page.wait_for_timeout(750)
        self.assertEqual(list(Path(self.directory.name).iterdir()), [])

    def test_missing_incomplete_or_duplicate_baseline_stops_before_generation(self):
        self.page.evaluate("document.querySelector('#table').remove()")
        with self.assertRaisesRegex(RuntimeError, 'DOWNLOAD_BASELINE_UNAVAILABLE'):
            self.execute(0)
        self.page.set_content('<table id=table><tbody></tbody></table>')
        self.page.evaluate("document.querySelector('tbody').innerHTML='<tr data-job-id=duplicate><td class=name>Report-123.csv</td></tr>'.repeat(1001)")
        with self.assertRaisesRegex(RuntimeError, 'DOWNLOAD_BASELINE_INCOMPLETE'):
            self.execute(0)
        self.page.evaluate("document.querySelector('tbody').innerHTML='<tr data-job-id=duplicate><td class=name>Report-123.csv</td></tr>'.repeat(2)")
        with self.assertRaisesRegex(RuntimeError, 'DOWNLOAD_IDENTITY_INVALID'):
            self.execute(0)

    def test_cancel_authorization_or_context_change_prevents_download(self):
        self.generate()
        self.execute(0)
        self.execute(1)
        self.context.cancellation_requested = lambda: True
        with self.assertRaisesRegex(RuntimeError, 'EXECUTION_CANCELLED'):
            self.execute(2)
        self.context.cancellation_requested = None
        class Revoked:
            def ensure_authenticated(self, page):
                raise RuntimeError('secret-auth-canary')
        self.context.auth_guard = Revoked()
        with self.assertRaisesRegex(RuntimeError, 'DOWNLOAD_AUTHORIZATION_REVOKED'):
            self.execute(2)
        self.context.auth_guard = None
        other = self.browser.new_page()
        try:
            self.context.page = other
            with self.assertRaisesRegex(RuntimeError, 'DOWNLOAD_CONTEXT_MISMATCH'):
                self.execute(2)
        finally:
            other.close()
        self.assertEqual(self.context.artifacts, [])

    def test_button_readiness_and_reordering_do_not_change_selected_job(self):
        self.generate()
        self.execute(0)
        self.execute(1)
        self.page.wait_for_timeout(120)
        self.page.evaluate('''() => {
            const row=document.querySelector('tr[data-job-id="request-new"]');
            const link=row.querySelector('a');link.setAttribute('aria-disabled','true');
            setTimeout(()=>{document.querySelector('tbody').append(row);link.removeAttribute('aria-disabled');},180);
        }''')
        self.assertEqual(Path(self.execute(2)).read_text(), 'new')

    def test_multiple_buttons_and_old_rebuilt_rows_cannot_download(self):
        self.generate()
        self.execute(0)
        self.execute(1)
        self.page.wait_for_timeout(120)
        self.page.evaluate("const row=document.querySelector('tr[data-job-id=\"request-new\"]'); row.querySelector('td:last-child').append(row.querySelector('a').cloneNode(true))")
        with self.assertRaisesRegex(RuntimeError, 'DOWNLOAD_BUTTON_AMBIGUOUS'):
            self.execute(2)
        self.page.evaluate("document.querySelector('tbody').innerHTML='<tr data-job-id=old><td class=name>Report-123.csv</td><td><a href=\"data:text/plain,old\">Download</a></td></tr>'")
        with patch('download_generation.monotonic', lambda: clock() * 1000):
            with self.assertRaisesRegex(RuntimeError, 'DOWNLOAD_GENERATION_TIMEOUT'):
                self.execute(2)
        self.assertEqual(self.context.artifacts, [])

    def test_dry_run_does_not_open_browser_or_keep_tokens(self):
        self.context.page = None
        self.context.dry_run = True
        result = RecipeRunner().run(self.recipe, self.context)
        self.assertIsNone(result.error)
        self.assertEqual(self.context.download_state, {})

    def test_two_real_contexts_share_central_and_finish_out_of_order(self):
        release_a, both_generated = threading.Event(), threading.Barrier(2)
        downloads, generated = [], set()
        lock = threading.Lock()
        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *_): pass
            def do_GET(self):
                route = self.path
                if route.startswith('/generate/'):
                    identity = route.rsplit('/', 1)[-1]
                    with lock: generated.add(identity)
                    both_generated.wait(timeout=15)
                    body = json.dumps({'id': identity}).encode()
                    content_type = 'application/json'
                elif route == '/list':
                    with lock:
                        ready = [identity for identity in sorted(generated) if identity == 'B' or release_a.is_set()]
                    body = ''.join(f'<tr data-job-id="{identity}"><td class=name>Report-123.csv</td><td><a href="/download/{identity}">Download</a></td></tr>' for identity in ready).encode()
                    content_type = 'text/html'
                elif route.startswith('/download/'):
                    identity = route.rsplit('/', 1)[-1]
                    with lock: downloads.append(identity)
                    if identity == 'B': release_a.set()
                    body, content_type = identity.encode(), 'text/csv'
                else:
                    identity = route.rsplit('/', 1)[-1]
                    body = ('''<button id=export>Generate</button><span style="display:inline-block;width:1px;height:1px" id=confirmation></span><table id=table><tbody></tbody></table>
                        <script>document.querySelector('#export').onclick=async()=>{
                        const result=await (await fetch('/generate/IDENTITY')).json();
                        document.querySelector('#confirmation').setAttribute('data-job-id',result.id);};
                        setInterval(async()=>{document.querySelector('tbody').innerHTML=await(await fetch('/list')).text();},50);</script>'''.replace('IDENTITY', identity)).encode()
                    content_type = 'text/html'
                self.send_response(200)
                self.send_header('Content-Type', content_type)
                if route.startswith('/download/'):
                    self.send_header('Content-Disposition', 'attachment; filename="Report-123.csv"')
                self.end_headers()
                self.wfile.write(body)
        server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        serving = threading.Thread(target=server.serve_forever, daemon=True)
        serving.start()
        results = {}
        def run(identity):
            try:
                with sync_playwright() as playwright:
                    browser = playwright.chromium.launch(channel='msedge', headless=True)
                    try:
                        page = browser.new_page(accept_downloads=True)
                        page.goto(f'http://127.0.0.1:{server.server_port}/view/{identity}')
                        context = ExecutionContext(page=page, variables={'pattern': 'Report-*.csv'},
                                                   downloads_dir=Path(self.directory.name)/identity)
                        result = RecipeRunner().run(generation_recipe(), context)
                        results[identity] = result.error or Path(context.artifacts[-1]['path']).read_text()
                        self.assertEqual(context.download_state, {})
                    finally: browser.close()
            except Exception as exc:
                results[identity] = type(exc).__name__ + ': ' + str(exc)
        threads = [threading.Thread(target=run, args=(identity,)) for identity in ('A', 'B')]
        try:
            for thread in threads: thread.start()
            for thread in threads: thread.join(35)
            self.assertFalse(any(thread.is_alive() for thread in threads))
            self.assertEqual(results, {'A': 'A', 'B': 'B'})
            self.assertEqual(downloads, ['B', 'A'])
        finally:
            release_a.set()
            server.shutdown(); server.server_close(); serving.join(3)


if __name__ == '__main__':
    unittest.main()
