"""Opt-in: recorded fixture -> API -> worker/Edge -> history UI -> download.

Only ephemeral databases, ports, sessions, processes and synthetic bytes.
Requires the frontend dependencies installed in this checkout.
"""
import hashlib
import importlib
import json
import os
from pathlib import Path
import socket
import subprocess
import tempfile
from threading import Thread
import time
import unittest
from urllib.parse import parse_qs, urlsplit
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import httpx
from playwright.sync_api import sync_playwright
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import uvicorn

from app.config import Settings, get_settings
from app.database import get_db
from app.main import app
from app.models import Base, Automation, AutomationVersion, utcnow
from app.security import SESSION_COOKIE_NAME, issue_session
from nexer_recorder.compiler import Recording
from nexer_recorder.scripts import recorder_script
from nexer_recorder.readiness import normalize_readiness
from nexer_worker.processor import WorkerExecutionProcessor
from nexer_worker.service import WorkerService

ROOT = Path(__file__).resolve().parents[3]


def free_port():
    with socket.socket() as connection:
        connection.bind(('127.0.0.1', 0))
        return connection.getsockname()[1]


class FixtureHandler(BaseHTTPRequestHandler):
    def log_message(self, *_args):
        pass

    def do_GET(self):
        if self.path.startswith('/report'):
            company = parse_qs(urlsplit(self.path).query).get('company', [''])[0]
            body = f'company,total\n{company},42\n'.encode()
            self.send_response(200)
            self.send_header('Content-Type', 'text/csv')
            self.send_header('Content-Disposition', 'attachment; filename="result.csv"')
        else:
            body = b'''<label for="company">Company</label><input id="company"
              oninput="document.querySelector('a').href='/report?company='+encodeURIComponent(this.value)">
              <a id="export" href="/report" download>Export</a>'''
            self.send_response(200)
            self.send_header('Content-Type', 'text/html')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers(); self.wfile.write(body)


@unittest.skipUnless(os.getenv('NEXER_RUN_ARTIFACT_E2E') == '1', 'Set NEXER_RUN_ARTIFACT_E2E=1 for isolated UI/Edge test')
class RecordedArtifactsE2E(unittest.TestCase):
    def test_recorded_flow_delivers_distinct_validated_files_in_history_ui(self):
        with tempfile.TemporaryDirectory(prefix='nexer-artifacts-e2e-') as directory:
            root = Path(directory)
            api_port, frontend_port = free_port(), free_port()
            frontend_origin = f'http://127.0.0.1:{frontend_port}'
            api_origin = f'http://127.0.0.1:{api_port}'
            settings = Settings(port=api_port, cors_origins=(frontend_origin,), downloads_root=str(root / 'downloads'))
            engine = create_engine('sqlite:///' + str(root / 'e2e.db'), connect_args={'check_same_thread': False})
            Base.metadata.create_all(engine)
            sessions = sessionmaker(engine, expire_on_commit=False)
            def database():
                with sessions() as db:
                    yield db
            app.dependency_overrides[get_db] = database
            app.dependency_overrides[get_settings] = lambda: settings
            main = importlib.import_module('app.main')
            old_settings = main.settings; main.settings = settings
            try:
                self._scenario(root, sessions, settings, frontend_origin, api_origin)
            finally:
                main.settings = old_settings
                app.dependency_overrides.clear()
                engine.dispose()

    def _scenario(self, root, sessions, settings, frontend_origin, api_origin):
        site = ThreadingHTTPServer(('127.0.0.1', 0), FixtureHandler)
        thread = Thread(target=site.serve_forever, daemon=True); thread.start()
        base_url = f'http://127.0.0.1:{site.server_port}/'
        server = uvicorn.Server(uvicorn.Config(app, host='127.0.0.1', port=settings.port, log_level='error', access_log=False))
        api_thread = Thread(target=server.run, daemon=True); api_thread.start()
        # Serve the real frontend with a temporary proxy config so all UI requests are same-origin.
        config = root / 'vite.config.mjs'
        config.write_text("export default {server:{proxy:{'/api':{target:" + json.dumps(api_origin) +
            ",changeOrigin:true,rewrite:path=>path.replace(/^\\/api/,'')}}}};", encoding='utf-8')
        env = os.environ.copy(); env['VITE_API_URL'] = frontend_origin + '/api'
        frontend = subprocess.Popen(['node', str(ROOT / 'apps/frontend/node_modules/vite/bin/vite.js'),
            '--host','127.0.0.1','--port',str(urlsplit(frontend_origin).port),'--strictPort','--config',str(config)],
            cwd=ROOT / 'apps/frontend', env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
        try:
            with httpx.Client(trust_env=False, timeout=2) as probe:
                for _ in range(100):
                    try:
                        if probe.get(api_origin + '/health').status_code == 200 and probe.get(frontend_origin).status_code == 200:
                            break
                    except httpx.HTTPError:
                        pass
                    time.sleep(.1)
                else:
                    self.fail('Isolated API/frontend did not become ready')
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(channel='msedge', headless=True)
                try:
                    recorder = browser.new_page()
                    recording = Recording('Generic artifact fixture')
                    def capture(source, event):
                        wait, event = normalize_readiness(event, recording.steps[-1])
                        if wait is not None: recording.accept(wait)
                        recording.accept(event)
                    recorder.expose_binding('nexerCapture', capture)
                    recorder.goto(base_url); recorder.evaluate(recorder_script())
                    recorder.locator('#company').fill('demonstration-canary')
                    with recorder.expect_download(): recorder.locator('#export').click()
                    recorder.wait_for_timeout(100)
                    recipe = recording.recipe()
                    self.assertNotIn('demonstration-canary', json.dumps(recipe))
                    download = next(step for step in recipe['steps'] if step['action'] == 'download')
                    # The browser supplies the real filename, independently of the dashboard fallback.
                    download['preserve_filename'] = True
                    recipe['steps'].append({'id':'validate','action':'validate_file','source_download':download['id'],
                        'min_size':1,'extensions':['.csv'],'calculate_checksum':True})
                    recorder.close()
                    with sessions() as db:
                        automation = Automation(code='GENERIC_ARTIFACT',name='Generic artifact',status='PUBLISHED',current_version=1)
                        db.add(automation); db.flush()
                        db.add(AutomationVersion(automation_id=automation.id,version=1,recipe=recipe,
                                                 test_status='PASSED',published_at=utcnow()))
                        db.commit(); automation_id = automation.id
                    token = issue_session('isolated-e2e',600)
                    worker = WorkerService(session_factory=sessions,worker_id='artifact-e2e',pid=os.getpid()); worker.register()
                    try:
                        processor = WorkerExecutionProcessor(session_factory=sessions,worker_service=worker,
                            downloads_root=root / 'downloads',page_factory=lambda *args: browser.new_page())
                        with httpx.Client(base_url=api_origin,headers={'Origin':frontend_origin},
                            cookies={SESSION_COOKIE_NAME:token},trust_env=False,timeout=10) as client:
                            outputs = []
                            for company in ('A','B'):
                                inputs = {name:(base_url if name == 'base_url' else 'wrong-fallback.csv' if name.startswith('download_file_') else company)
                                          for name in recipe['variables']}
                                response = client.post('/executions',json={'name':'Synthetic '+company,
                                    'automation_ids':[automation_id],'inputs':inputs})
                                self.assertEqual(response.status_code,201,response.text)
                                execution_id = response.json()['id']
                                self.assertEqual(processor.process_once().status,'SUCCEEDED')
                                artifacts = client.get(f'/executions/{execution_id}/artifacts').json()['items']
                                self.assertEqual(len(artifacts),1)
                                expected = f'company,total\n{company},42\n'.encode()
                                self.assertEqual(artifacts[0]['checksum'],hashlib.sha256(expected).hexdigest())
                                ui = browser.new_page()
                                ui.context.add_cookies([{'name':SESSION_COOKIE_NAME,'value':token,'url':frontend_origin,'httpOnly':True,'sameSite':'Strict'}])
                                ui.goto(frontend_origin + f'/executions/{execution_id}')
                                with ui.expect_download() as completed:
                                    ui.get_by_role('button',name='Baixar result.csv',exact=True).click()
                                output = root / f'ui-{company}.csv'; completed.value.save_as(output)
                                self.assertEqual(output.read_bytes(),expected)
                                outputs.append(output.read_bytes()); ui.close()
                            self.assertNotEqual(outputs[0],outputs[1])
                    finally:
                        worker.stop()
                finally:
                    browser.close()
        finally:
            if frontend.poll() is None:
                if os.name == 'nt':
                    subprocess.run(['taskkill','/PID',str(frontend.pid),'/T','/F'],capture_output=True,timeout=15,
                                   creationflags=subprocess.CREATE_NO_WINDOW)
                else:
                    frontend.terminate()
                frontend.wait(timeout=15)
            server.should_exit = True; api_thread.join(timeout=15)
            site.shutdown(); site.server_close(); thread.join(timeout=5)


if __name__ == '__main__':
    unittest.main()
