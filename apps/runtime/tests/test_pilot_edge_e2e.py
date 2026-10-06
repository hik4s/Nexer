import json
import os
import threading
import unittest
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import tempfile

from browser_manager import BrowserManager
from context import ExecutionContext
from recipe import validate_recipe
from runner import RecipeRunner


ROOT = Path(__file__).resolve().parents[1]


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *_args):
        pass


class PilotEdgeE2ETests(unittest.TestCase):
    @unittest.skipUnless(
        os.getenv("RELATPY_RUN_EDGE_E2E") == "1",
        "Set RELATPY_RUN_EDGE_E2E=1 to run the real Edge smoke",
    )
    def test_local_pilot_downloads_and_validates_file(self):
        recipe = validate_recipe(
            json.loads(
                (ROOT / "recipes" / "pilot-smoke.json").read_text(
                    encoding="utf-8"
                )
            )
        )

        with tempfile.TemporaryDirectory() as root:
            root_path = Path(root)
            page = root_path / "index.html"
            page.write_text(
                """<!doctype html>
<html lang="pt-BR">
  <body>
    <label>Empresa <input id="company"></label>
    <button id="prepare" onclick="document.body.dataset.company=document.getElementById('company').value">Preparar</button>
    <a id="download" href="/relatpy-pilot.xlsx" download>Baixar relatório</a>
  </body>
</html>
""",
                encoding="utf-8",
            )
            (root_path / "relatpy-pilot.xlsx").write_bytes(
                b"PK\x03\x04RelatPy pilot test"
            )

            server = ThreadingHTTPServer(
                ("127.0.0.1", 0),
                partial(QuietHandler, directory=root),
            )
            thread = threading.Thread(
                target=server.serve_forever,
                daemon=True,
            )
            thread.start()

            browser = BrowserManager(
                headless=True,
                temp_root=root_path / "downloads",
            )
            context = None
            try:
                browser.start()
                context = browser.create_context("edge-e2e")
                page_obj = context.new_page()

                events = []
                runtime_context = ExecutionContext(
                    page=page_obj,
                    variables={
                        "base_url": f"http://127.0.0.1:{server.server_port}/index.html",
                        "company": "001",
                    },
                    downloads_dir=root_path / "downloads" / "edge-e2e",
                    emit=events.append,
                )

                result = RecipeRunner().run(recipe, runtime_context)

                self.assertEqual(result.completed_steps, 5)
                self.assertIsNone(result.failed_step_id)
                artifact = root_path / "downloads" / "edge-e2e" / "relatpy-pilot.xlsx"
                self.assertTrue(artifact.is_file())
                self.assertGreater(artifact.stat().st_size, 0)
                self.assertTrue(any(e["type"] == "checkpoint" for e in events))
            finally:
                if context is not None:
                    context.close()
                browser.close()
                server.shutdown()
                server.server_close()


if __name__ == "__main__":
    unittest.main()
