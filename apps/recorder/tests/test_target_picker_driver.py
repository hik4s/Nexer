import os
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest.mock import Mock, patch
from playwright.sync_api import sync_playwright
from nexer_recorder.target_picker import pick_target


@unittest.skipUnless(os.getenv('NEXER_RUN_RECORDER_E2E') == '1', 'Real Edge target driver')
class TargetDriverTests(unittest.TestCase):
    def test_real_driver_selects_once_blocks_post_and_closes_owned_browser(self):
        posts=[]
        class Handler(BaseHTTPRequestHandler):
            def log_message(self,*_): pass
            def do_GET(self):
                self.send_response(200);self.send_header('Content-Type','text/html');self.end_headers()
                self.wfile.write(b'<form method="post"><button id="run" onclick="window.effects++">Run</button></form><script>window.effects=0;</script>')
            def do_POST(self):
                posts.append(True);self.send_response(200);self.end_headers()
        server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
        threading.Thread(target=server.serve_forever,daemon=True).start()
        try:
            with sync_playwright() as real:
                browser=real.chromium.launch(channel='msedge',headless=True)
                original_context=browser.new_context
                def new_context(**options):
                    context=original_context(**options);original_page=context.new_page
                    def new_page():
                        page=original_page();original_wait=page.wait_for_timeout;stage=[0]
                        def wait(milliseconds):
                            original_wait(milliseconds)
                            if stage[0]==0:
                                page.get_by_role('button',name='Selecionar alvo',exact=True).click();stage[0]=1
                            elif stage[0]==1:
                                page.evaluate("() => fetch('/effect',{method:'POST'}).catch(()=>{})")
                                page.locator('#run').click();original_wait(40)
                                self.assertEqual(page.evaluate('effects'),0);stage[0]=2
                        page.wait_for_timeout=wait
                        return page
                    context.new_page=new_page
                    return context
                browser.new_context=new_context
                factory=Mock();factory.__enter__=Mock(return_value=factory);factory.__exit__=Mock(return_value=False)
                factory.chromium.launch.return_value=browser
                phases=[]
                with patch('nexer_recorder.target_picker.sync_playwright',return_value=factory):
                    target=pick_target({'url':f'http://127.0.0.1:{server.server_port}/','kind':'element'},threading.Event(),phases.append,headless=True,timeout=10)
                self.assertEqual(target,{'selector':'#run'})
                self.assertEqual(phases,['SELECTING']);self.assertEqual(posts,[])
                self.assertFalse(browser.is_connected())
        finally:server.shutdown();server.server_close()
