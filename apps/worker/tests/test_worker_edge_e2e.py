import json
import os
import tempfile
import threading
import unittest
from datetime import datetime, timezone
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import sessionmaker

from app.enums import ExecutionAutomationStatus, ExecutionStatus
from app.models import Automation, AutomationVersion, Execution, ExecutionAutomation
from browser_manager import BrowserManager
from relatpy_worker.processor import WorkerExecutionProcessor
from relatpy_worker.service import WorkerService


BACKEND_ROOT = Path(__file__).resolve().parents[2] / "backend"


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *_args):
        pass


class WorkerEdgeE2ETests(unittest.TestCase):
    @unittest.skipUnless(
        os.getenv("RELATPY_RUN_EDGE_E2E") == "1",
        "Set RELATPY_RUN_EDGE_E2E=1 to run the real Worker + Edge smoke",
    )
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.tmp.name)
        db_path = cls.root / "worker-edge.db"

        config = Config(str(BACKEND_ROOT / "alembic.ini"))
        config.set_main_option("sqlalchemy.url", f"sqlite:///{db_path}")
        command.upgrade(config, "head")

        cls.engine = create_engine(
            f"sqlite:///{db_path}",
            connect_args={"check_same_thread": False},
        )
        cls.session_factory = sessionmaker(
            bind=cls.engine,
            autoflush=False,
            autocommit=False,
        )

        cls.web_root = cls.root / "site"
        cls.web_root.mkdir()
        (cls.web_root / "index.html").write_text(
            """<!doctype html>
<html lang="pt-BR">
  <body>
    <input id="company">
    <a id="download" href="/relatpy-pilot.xlsx" download>Baixar</a>
  </body>
</html>
""",
            encoding="utf-8",
        )
        (cls.web_root / "relatpy-pilot.xlsx").write_bytes(
            b"PK\x03\x04RelatPy worker e2e"
        )

        cls.server = ThreadingHTTPServer(
            ("127.0.0.1", 0),
            partial(QuietHandler, directory=str(cls.web_root)),
        )
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.engine.dispose()
        cls.tmp.cleanup()

    def setUp(self):
        db = self.session_factory()
        try:
            for table in (
                "events",
                "artifacts",
                "checkpoints",
                "execution_automations",
                "executions",
                "automation_versions",
                "destinations",
                "automations",
                "workers",
            ):
                db.execute(text(f"DELETE FROM {table}"))
            db.commit()
        finally:
            db.close()

    def test_worker_claims_execution_runs_edge_recipe_and_persists_success(self):
        db = self.session_factory()
        try:
            automation = Automation(
                code="WORKER_EDGE_E2E",
                name="Worker Edge E2E",
                status="PUBLISHED",
                current_version=1,
            )
            db.add(automation)
            db.flush()

            db.add(
                AutomationVersion(
                    automation_id=automation.id,
                    version=1,
                    recipe={
                        "schema_version": 1,
                        "name": "Worker Edge E2E",
                        "variables": {
                            "base_url": {"type": "string", "required": True},
                            "company": {"type": "string", "required": True},
                        },
                        "steps": [
                            {
                                "id": "open",
                                "action": "navigate",
                                "url": "{{base_url}}",
                            },
                            {
                                "id": "fill_company",
                                "action": "fill",
                                "selector": "#company",
                                "value": "{{company}}",
                            },
                            {
                                "id": "download",
                                "action": "download",
                                "selector": "#download",
                                "filename": "relatpy-pilot.xlsx",
                            },
                            {
                                "id": "validate",
                                "action": "validate_file",
                                "path": "relatpy-pilot.xlsx",
                                "min_size": 1,
                                "extensions": [".xlsx"],
                            },
                        ],
                        "output": {"type": "file"},
                    },
                    test_status="PASSED",
                    published_at=datetime.now(timezone.utc).replace(tzinfo=None),
                )
            )

            execution = Execution(
                name="Worker Edge E2E",
                status=ExecutionStatus.QUEUED.value,
                test_mode=True,
                send_to_network=False,
                keep_local_copy=True,
                overwrite_existing=False,
                cancel_requested=False,
                inputs={
                    "base_url": f"http://127.0.0.1:{self.server.server_port}/index.html",
                    "company": "001",
                },
            )
            db.add(execution)
            db.flush()
            db.add(
                ExecutionAutomation(
                    execution_id=execution.id,
                    automation_id=automation.id,
                    automation_version=1,
                    status=ExecutionAutomationStatus.PENDING.value,
                    stage="CREATED",
                    attempts=0,
                )
            )
            db.commit()
            execution_id = execution.id
        finally:
            db.close()

        browser = BrowserManager(
            headless=True,
            temp_root=self.root / "downloads",
        )
        worker = WorkerService(
            session_factory=self.session_factory,
            worker_id="worker-edge-e2e",
            concurrency_limit=1,
            hostname="e2e",
            pid=12345,
        )

        browser.start()
        worker.register()

        processor = WorkerExecutionProcessor(
            session_factory=self.session_factory,
            worker_service=worker,
            page_factory=lambda execution, item, recipe: browser.create_page(
                f"{execution.id}-{item.id}"
            ),
            downloads_root=self.root / "downloads",
        )

        try:
            result = processor.process_once()
        finally:
            worker.stop()
            browser.close()

        self.assertEqual(result.execution_id, execution_id)
        self.assertEqual(result.status, ExecutionStatus.SUCCEEDED.value)

        artifact = (
            self.root
            / "downloads"
            / str(execution_id)
            / "1"
            / "relatpy-pilot.xlsx"
        )
        self.assertTrue(artifact.is_file())
        self.assertGreater(artifact.stat().st_size, 0)

        db = self.session_factory()
        try:
            stored = db.get(Execution, execution_id)
            item = db.scalar(
                select(ExecutionAutomation).where(
                    ExecutionAutomation.execution_id == execution_id
                )
            )
            self.assertEqual(stored.status, ExecutionStatus.SUCCEEDED.value)
            self.assertEqual(item.status, ExecutionAutomationStatus.SUCCEEDED.value)
        finally:
            db.close()


if __name__ == "__main__":
    unittest.main()
