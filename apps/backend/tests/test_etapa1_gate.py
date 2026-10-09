import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from alembic import command
from alembic.config import Config
from test_client import AuthenticatedTestClient as TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import get_db
from app.main import app
from app.models import Execution, ExecutionAutomation
from app.enums import ExecutionAutomationStatus, ExecutionStatus
from nexer_worker.processor import WorkerExecutionProcessor
from nexer_worker.service import WorkerService


BACKEND_ROOT = Path(__file__).resolve().parents[1]


class FakeLocator:
    def __init__(self, calls):
        self.calls = calls

    def click(self, **_kwargs):
        self.calls.append(("click",))

    def fill(self, value, **_kwargs):
        self.calls.append(("fill", value))


class FakePage:
    def __init__(self):
        self.calls = []

    def goto(self, url, **_kwargs):
        self.calls.append(("goto", url))

    def locator(self, selector):
        return FakeLocator(self.calls)


class Etapa1GateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        db_path = Path(cls.tmp.name) / "gate.db"

        config = Config(str(BACKEND_ROOT / "alembic.ini"))
        config.set_main_option("sqlalchemy.url", f"sqlite:///{db_path}")
        command.upgrade(config, "head")

        cls.engine = create_engine(
            f"sqlite:///{db_path}",
            connect_args={"check_same_thread": False},
        )
        cls.session_factory = sessionmaker(bind=cls.engine, autoflush=False, autocommit=False)

        def override_get_db():
            db = cls.session_factory()
            try:
                yield db
            finally:
                db.close()

        app.dependency_overrides[get_db] = override_get_db
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls):
        app.dependency_overrides.clear()
        cls.engine.dispose()
        cls.tmp.cleanup()

    def test_api_to_worker_to_runtime_gate(self):
        automation = self.client.post(
            "/automations",
            json={
                "code": "ETAPA1_GATE",
                "name": "Etapa 1 Gate",
            },
        )
        self.assertEqual(automation.status_code, 201)
        automation_id = automation.json()["id"]

        recipe = {
            "schema_version": 1,
            "name": "Etapa 1 Gate Recipe",
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
                    "id": "fill",
                    "action": "fill",
                    "selector": "#company",
                    "value": "{{company}}",
                },
            ],
            "output": {"type": "file"},
        }

        version = self.client.post(
            f"/automations/{automation_id}/versions",
            json={"recipe": recipe},
        )
        self.assertEqual(version.status_code, 201)

        version_number = version.json()["version"]

        self.assertEqual(
            self.client.post(
                f"/automations/{automation_id}/versions/{version_number}/test"
            ).status_code,
            200,
        )
        self.assertEqual(
            self.client.post(
                f"/automations/{automation_id}/versions/{version_number}/publish"
            ).status_code,
            200,
        )

        execution = self.client.post(
            "/executions",
            json={
                "name": "Etapa 1 Gate Execution",
                "automation_ids": [automation_id],
                "test_mode": True,
                "inputs": {
                    "base_url": "https://example.test/gate",
                    "company": "001",
                },
            },
        )
        self.assertEqual(execution.status_code, 201)
        execution_id = execution.json()["id"]

        worker = WorkerService(
            session_factory=self.session_factory,
            worker_id="etapa1-gate-worker",
            concurrency_limit=1,
            hostname="gate",
            pid=123,
        )
        worker.register()

        pages = []

        def page_factory(_execution, _item, _recipe):
            page = FakePage()
            pages.append(page)
            return page

        processor = WorkerExecutionProcessor(
            session_factory=self.session_factory,
            worker_service=worker,
            page_factory=page_factory,
            downloads_root=Path(self.tmp.name) / "downloads",
        )

        result = processor.process_once()
        worker.stop()

        self.assertEqual(result.execution_id, execution_id)
        self.assertEqual(result.status, ExecutionStatus.SUCCEEDED.value)
        self.assertEqual(
            pages[0].calls[0],
            ("goto", "https://example.test/gate"),
        )
        self.assertIn(("fill", "001"), pages[0].calls)

        db = self.session_factory()
        try:
            stored = db.get(Execution, execution_id)
            item = db.query(ExecutionAutomation).filter_by(
                execution_id=execution_id
            ).one()

            self.assertEqual(
                stored.status,
                ExecutionStatus.SUCCEEDED.value,
            )
            self.assertEqual(
                item.status,
                ExecutionAutomationStatus.SUCCEEDED.value,
            )
        finally:
            db.close()


if __name__ == "__main__":
    unittest.main()
