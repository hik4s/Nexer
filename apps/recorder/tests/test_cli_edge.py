import contextlib
import functools
import faulthandler
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import importlib.util
import json
import os
import re
from pathlib import Path
import tempfile
import threading
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from playwright.sync_api import sync_playwright
from context import ExecutionContext
from runner import RecipeRunner
from actions import create_default_registry

ROOT = Path(__file__).resolve().parents[3]


@unittest.skipUnless(os.getenv("NEXER_RUN_RECORDER_E2E") == "1", "Synthetic Edge recorder CLI opt-in")
class RecorderCliTests(unittest.TestCase):
    def test_https_preparation_route_password_start_and_finish(self):
        faulthandler.dump_traceback_later(30)
        self.addCleanup(faulthandler.cancel_dump_traceback_later)
        spec = importlib.util.spec_from_file_location("record_https_cli", ROOT / "scripts/record_recipe.py")
        recorder = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(recorder)
        with tempfile.TemporaryDirectory() as directory, sync_playwright() as playwright:
            progress, aborted, redirects = [], [], []
            destination = "https://example.invalid/sgind/#/report"
            def launch(**options):
                browser = playwright.chromium.launch(**{**options, "headless": True})
                original_context = browser.new_context
                def new_context(**kwargs):
                    context = original_context(**kwargs)
                    original_route, original_page = context.route, context.new_page
                    def route(pattern, handler):
                        def fixture_route(real):
                            class FixtureRoute:
                                request = real.request
                                def fetch(self, **kw):
                                    self.assert_redirects = kw
                                    redirects.append(kw)
                                    return SimpleNamespace(status=302 if real.request.url.endswith('/redirect') else 200)
                                def fulfill(self, **kw):
                                    html = '<label>Preparation metadata<input id="company"></label><input type="password"><button id="login">Login</button>'
                                    if real.request.url.endswith('/popup'): html = html.replace('Preparation metadata', 'Report popup field')
                                    real.fulfill(status=200, content_type='text/html', body=html)
                                def abort(self):
                                    aborted.append(True)
                                    real.abort()
                            handler(FixtureRoute())
                        original_route(pattern, fixture_route)
                    context.route = route
                    def new_page():
                        page = original_page()
                        original_wait = page.wait_for_timeout
                        phase = [0]
                        preparation_tabs = []
                        def interact(_):
                            original_wait(150)
                            if phase[0] == 0:
                                page.locator('#company').fill('preparation-canary')
                                page.locator('input[type=password]').fill('password-canary')
                                page.locator('#login').click()
                                page.get_by_role('button', name='Iniciar gravação', exact=True).click()
                            elif phase[0] == 1:
                                self.assertTrue(page.get_by_text('Conclua o login manual antes de iniciar.').is_visible())
                                page.evaluate("document.querySelector('input[type=password]').remove(); const frame=document.createElement('iframe'); frame.srcdoc='<input type=password>'; document.body.append(frame)")
                                page.frame_locator('iframe').locator('input').wait_for()
                                page.get_by_role('button', name='Iniciar gravação', exact=True).click()
                            elif phase[0] == 2:
                                self.assertTrue(page.get_by_text('Conclua o login manual antes de iniciar.').is_visible())
                                page.evaluate("document.querySelector('iframe').remove(); location.hash='/wrong'")
                                page.get_by_role('button', name='Iniciar gravação', exact=True).click()
                            elif phase[0] == 3:
                                self.assertTrue(page.get_by_text('Abra a página e a rota configuradas antes de iniciar.').is_visible())
                                page.evaluate("location.hash='/report'; document.querySelector('label').firstChild.textContent='Report field'")
                                preparation_tabs.append(original_page())
                                preparation_tabs[0].goto('https://example.invalid/preparation')
                                preparation_tabs[0].locator('#company').fill('prep-tab-canary')
                                page.get_by_role('button', name='Iniciar gravação', exact=True).click()
                            elif phase[0] == 4:
                                self.assertEqual(progress, [])
                                self.assertTrue(page.get_by_text('Feche as abas abertas durante a preparação e volte à página original.').is_visible())
                                preparation_tabs[0].close()
                                page.get_by_role('button', name='Iniciar gravação', exact=True).click()
                            else:
                                self.assertEqual(progress, ['started'])
                                page.locator('#company').fill('before-refresh-canary')
                                page.reload()
                                page.get_by_role('button', name='Parar gravação', exact=True).wait_for()
                                page.evaluate("document.querySelector('label').firstChild.textContent='Report field'")
                                page.locator('#company').fill('recording-canary')
                                page.evaluate("const button=document.createElement('button'); button.id='open-popup'; button.textContent='Report popup'; button.onclick=()=>window.open('/popup'); document.body.append(button)")
                                with page.expect_popup() as popup_info:
                                    page.locator('#open-popup').click()
                                popup = popup_info.value
                                popup.wait_for_load_state()
                                popup.evaluate("document.querySelector('label').firstChild.textContent='Report popup field'")
                                popup.locator('#company').fill('popup-recording-canary')
                                page.locator('#company').fill('main-recording-canary')
                                popup.close()
                                page.evaluate("fetch('https://cross-origin.invalid/resource').catch(() => {})")
                                page.evaluate("fetch('/redirect').catch(() => {})")
                                page.get_by_role('button', name='Parar gravação', exact=True).click()
                            phase[0] += 1
                        page.wait_for_timeout = interact
                        return page
                    context.new_page = new_page
                    return context
                browser.new_context = new_context
                return browser
            output = Path(directory) / 'recipe.json'
            runtime = SimpleNamespace(chromium=SimpleNamespace(launch=launch))
            with patch.object(recorder, 'sync_playwright', lambda: contextlib.nullcontext(runtime)), patch('sys.argv', ['record_recipe.py', '--url', destination, '--output', str(output)]):
                recorder.main(on_started=lambda: progress.append('started'))
            recipe = json.loads(output.read_text(encoding='utf-8'))
            self.assertEqual(len(recipe['steps']), 9)
            self.assertEqual([step['index'] for step in recipe['steps'] if step['action'] == 'switch_tab'], [1, 0, 1])
            self.assertEqual(recipe['variables']['company']['label'], 'Preparation metadata')
            self.assertTrue(aborted)
            self.assertEqual(redirects, [{'max_redirects': 0}] * 5)
            self.assertGreaterEqual(len(aborted), 2)
            for canary in ('prep-tab-canary', 'preparation-canary', 'password-canary', 'recording-canary', 'before-refresh-canary'):
                self.assertNotIn(canary, json.dumps(recipe))

    def test_async_icon_export_is_matched_to_immediately_preceding_click(self):
        """An unlabeled icon downloads asynchronously; no filename enters the recipe."""
        spec = importlib.util.spec_from_file_location("record_async_cli", ROOT / "scripts/record_recipe.py")
        recorder = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(recorder)

        class Handler(SimpleHTTPRequestHandler):
            def log_message(self, *_):
                pass
            def do_GET(self):
                if self.path == "/generated":
                    self.send_response(200)
                    self.send_header("Content-Type", "text/csv")
                    self.send_header("Content-Disposition", 'attachment; filename="canary-secret-report.csv"')
                    self.end_headers()
                    self.wfile.write(b"safe,synthetic\n")
                    return
                self.send_response(200)
                self.send_header("Content-Type", "text/html")
                self.end_headers()
                self.wfile.write(b'<button id="icon" title="Exportar">&#8595;</button>')
        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        try:
            with tempfile.TemporaryDirectory() as directory, sync_playwright() as playwright:
                def launch(**options):
                    browser = playwright.chromium.launch(**{**options, "headless": True})
                    original_context = browser.new_context
                    def new_context(**kwargs):
                        context = original_context(**kwargs)
                        original_new_page = context.new_page
                        def new_page():
                            page = original_new_page()
                            def interact(_):
                                page.evaluate("""() => {
                                    document.querySelector('#icon').addEventListener('click', () => {
                                        setTimeout(() => { window.location.href = '/generated'; }, 180);
                                    });
                                }""")
                                with page.expect_download(timeout=8000):
                                    page.locator("#icon").click()
                                page.wait_for_timeout = lambda _: None
                                page.get_by_role("button", name="Parar gravação", exact=True).click()
                            page.wait_for_timeout = interact
                            return page
                        context.new_page = new_page
                        return context
                    browser.new_context = new_context
                    return browser
                output = Path(directory) / "recipe.json"
                runtime = SimpleNamespace(chromium=SimpleNamespace(launch=launch))
                with patch.object(recorder, "sync_playwright", lambda: contextlib.nullcontext(runtime)), patch("sys.argv", [
                    "record_recipe.py", "--url", f"http://127.0.0.1:{server.server_port}/report", "--output", str(output)
                ]):
                    recorder.main()
                recipe = json.loads(output.read_text(encoding="utf-8"))
                self.assertEqual([step["action"] for step in recipe["steps"]], ["navigate", "download"])
                self.assertIn("button:nth-of-type(1)", recipe["steps"][1]["selector"])
                self.assertNotIn("canary-secret-report.csv", json.dumps(recipe))
        finally:
            server.shutdown()
            server.server_close()

    def test_cli_saves_parameterized_draft_after_window_closes(self):
        faulthandler.dump_traceback_later(45)
        self.addCleanup(faulthandler.cancel_dump_traceback_later)
        spec = importlib.util.spec_from_file_location("record_recipe_cli", ROOT / "scripts/record_recipe.py")
        recorder = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(recorder)
        class Handler(SimpleHTTPRequestHandler):
            def log_message(self, *_):
                pass
        handler = functools.partial(Handler, directory=str(ROOT / "apps/recorder/fixtures"))
        server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with tempfile.TemporaryDirectory() as directory, sync_playwright() as playwright:
                replacements = {}
                def remember(page, selector, value, frames=()):
                    location = page.locator(selector).evaluate("element => window.__nexerStructuralSelector(element)")
                    replacements[(tuple(frames), location)] = value
                def launch(**options):
                    browser = playwright.chromium.launch(**{**options, "headless": True})
                    original_context = browser.new_context
                    def new_context(**kwargs):
                        context = original_context(**kwargs)
                        original_page = context.new_page
                        def new_page():
                            page = original_page()
                            original_wait = page.wait_for_timeout
                            def interact_and_close(_):
                                page.locator("#period_start").fill("2031-02-17")
                                page.locator("#period_end").fill("2031-03-29")
                                page.locator("#company").fill("recorded-company-canary")
                                page.locator("#regional").select_option("north")
                                for selector, value in [("#notes", "New notes"), ("#enabled", False), ("#amount", "9"),
                                                        ("#color", "#abcdef"), ("#choices", ["two"]), ("#editor", "New editable text"),
                                                        ("#custom", "Sul fictício"), ("#group", "detailed")]:
                                    remember(page, selector, value)
                                page.locator("#notes").fill("recorded-notes-canary")
                                page.locator("#enabled").check()
                                page.locator('[value="compact"]').check()
                                page.locator("#amount").evaluate("element => {element.value='3'; element.dispatchEvent(new Event('input', {bubbles:true}));}")
                                page.locator("#color").evaluate("element => {element.value='#112233'; element.dispatchEvent(new Event('input', {bubbles:true}));}")
                                page.locator("#choices").select_option(["one"])
                                page.locator("#editor").fill("recorded-editor-canary")
                                page.locator('#custom [role="option"]').first.click()
                                page.locator("#arbitrary").click()
                                frame = page.frames[1]
                                frame_selector = page.locator("iframe").evaluate("element => window.__nexerStructuralSelector(element)")
                                remember(frame, "#inner", "New internal value", [frame_selector])
                                frame.locator("#inner").fill("recorded-frame-canary")
                                frame.locator("#inner_button").click()
                                with page.expect_popup() as popup_info:
                                    page.locator("#popup").click()
                                popup = popup_info.value
                                popup.wait_for_load_state()
                                remember(popup, "#popup_field", "New popup value")
                                popup.locator("#popup_field").fill("recorded-popup-canary")
                                popup.locator("#popup_button").click()
                                original_wait(150)
                                popup.close()
                                page.locator("#generate").click()
                                with page.expect_download():
                                    page.locator("#download").click()
                                original_wait(250)
                                page.close()
                            page.wait_for_timeout = interact_and_close
                            return page
                        context.new_page = new_page
                        return context
                    browser.new_context = new_context
                    return browser
                output = Path(directory) / "recipe.json"
                runtime = SimpleNamespace(chromium=SimpleNamespace(launch=launch))
                with patch.object(recorder, "sync_playwright", lambda: contextlib.nullcontext(runtime)), patch("sys.argv", [
                    "record_recipe.py", "--url", f"http://127.0.0.1:{server.server_port}/report.html", "--output", str(output)
                ]):
                    recorder.main()
                exported = output.read_text(encoding="utf-8")
                self.assertNotIn("2031-02-17", exported)
                self.assertNotIn(str(server.server_port), exported)
                self.assertEqual(json.loads(exported)["steps"][1]["value"], "{{period_start}}")
                for canary in ("2031-03-29", "recorded-company-canary", "recorded-notes-canary", "recorded-editor-canary", "recorded-frame-canary", "recorded-popup-canary", "#112233", "dados-ficticios.csv"):
                    self.assertNotIn(canary, exported)
                recipe = json.loads(exported)
                inputs = {"base_url": f"http://127.0.0.1:{server.server_port}/report.html", "period_start": "2032-04-01",
                          "period_end": "2032-04-30", "company": "New company", "regional": "south"}
                for step in recipe["steps"]:
                    if "value" in step:
                        name = re.fullmatch(r"{{(\w+)}}", step["value"])[1]
                        if name not in inputs:
                            inputs[name] = replacements[(tuple(step.get("frames", [])), step["selector"])]
                    if step["action"] == "download":
                        inputs[re.fullmatch(r"{{(\w+)}}", step["filename"])[1]] = "new-report.csv"
                browser = playwright.chromium.launch(channel="msedge", headless=True, args=["--disable-features=msDownloadsHub"])
                try:
                    replay_context = browser.new_context(accept_downloads=True)
                    replay_page = replay_context.new_page()
                    context = ExecutionContext(page=replay_page, variables=inputs, downloads_dir=directory)
                    registry = create_default_registry()
                    original_registry = create_default_registry()
                    def click(step, context):
                        if context.page.url.endswith("/popup.html"):
                            self.assertEqual(context.page.locator("#popup_field").input_value(), "New popup value")
                        original_registry.execute("click", step, context)
                    registry.register("click", click)
                    result = RecipeRunner(registry=registry).run(recipe, context)
                    self.assertIsNone(result.failed_step_id, result.error)
                    self.assertEqual(replay_page.locator("#period_start").input_value(), "2032-04-01")
                    self.assertEqual(replay_page.locator("#period_end").input_value(), "2032-04-30")
                    self.assertEqual(replay_page.locator("#company").input_value(), "New company")
                    self.assertEqual(replay_page.locator("#regional").input_value(), "south")
                    self.assertFalse(replay_page.locator("#enabled").is_checked())
                    self.assertTrue(replay_page.locator('[value="detailed"]').is_checked())
                    self.assertEqual(replay_page.locator("#amount").input_value(), "9")
                    self.assertEqual(replay_page.locator("#color").input_value(), "#abcdef")
                    self.assertEqual(replay_page.locator("#editor").inner_text(), "New editable text")
                    self.assertEqual(replay_page.locator("#custom").get_attribute("data-selection"), "south")
                    self.assertEqual(replay_page.frame_locator("iframe").locator("#inner").input_value(), "New internal value")
                    self.assertEqual(len(replay_context.pages), 1)
                    self.assertTrue((Path(directory) / "new-report.csv").is_file())
                finally:
                    browser.close()
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)
