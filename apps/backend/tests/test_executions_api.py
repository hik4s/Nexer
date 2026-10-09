import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from alembic import command
from alembic.config import Config
from test_client import AuthenticatedTestClient as TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.database import get_db
from app.enums import AutomationStatus
from app.main import app
from app.models import Event, Execution
from app.models import Automation, AutomationVersion


BACKEND_ROOT = Path(__file__).resolve().parents[1]


class ExecutionsApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        db_path = Path(cls.tmp.name) / "nexer.db"

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
            ):
                db.execute(text(f"DELETE FROM {table}"))
            db.commit()
        finally:
            db.close()

    def _seed_published_automation(self):
        db = self.session_factory()
        try:
            automation = Automation(
                code="PUBLICADA",
                name="Automação publicada",
                status=AutomationStatus.PUBLISHED.value,
                current_version=1,
            )
            db.add(automation)
            db.flush()
            db.add(
                AutomationVersion(
                    automation_id=automation.id,
                    version=1,
                    recipe={
                        "version": 1,
                        "name": "piloto",
                        "steps": [],
                    },
                    created_at=datetime.now(timezone.utc).replace(tzinfo=None),
                )
            )
            db.commit()
            return automation.id
        finally:
            db.close()

    def test_corporate_credentials_are_rejected_until_adapter_validated(self):
        from sqlalchemy import select, func
        automation_id = self._seed_published_automation()
        response = self.client.post("/executions", json={
            "name": "Corporate test", "automation_ids": [automation_id],
            "corporate_credentials": {"SGIND": {"username": "canary-user", "password": "canary-secret"}}})
        self.assertEqual(response.status_code, 409)
        self.assertNotIn("canary", response.text)
        with self.session_factory() as db:
            self.assertEqual(db.scalar(select(func.count()).select_from(Execution)), 0)

    def test_corporate_envelope_repr_hides_secrets(self):
        from app.schemas_execution import ExecutionCreate
        payload = ExecutionCreate(name="Safe", automation_ids=[1],
            corporate_credentials={"SGIND": {"username": "canary-user", "password": "canary-secret"}})
        self.assertNotIn("canary", repr(payload))
        self.assertEqual(payload.corporate_credentials["SGIND"].password.get_secret_value(), "canary-secret")

    def test_create_and_read_execution(self):
        automation_id = self._seed_published_automation()

        response = self.client.post(
            "/executions",
            json={
                "name": "Execução piloto",
                "requested_by": "teste",
                "period_start": "2026-10-01T00:00:00",
                "period_end": "2026-10-05T23:59:59",
                "automation_ids": [automation_id],
                "send_to_network": False,
                "keep_local_copy": True,
                "overwrite_existing": False,
                "test_mode": True,
            },
        )

        self.assertEqual(response.status_code, 201)
        body = response.json()
        self.assertEqual(body["name"], "Execução piloto")
        self.assertEqual(body["status"], "QUEUED")
        self.assertFalse(body["cancel_requested"])
        self.assertEqual(body["items"][0]["automation_id"], automation_id)
        self.assertEqual(body["items"][0]["automation_version"], 1)
        self.assertEqual(body["items"][0]["status"], "PENDING")
        self.assertEqual(body["items"][0]["stage"], "CREATED")

        fetched = self.client.get(f"/executions/{body['id']}")
        self.assertEqual(fetched.status_code, 200)
        self.assertEqual(fetched.json()["id"], body["id"])
        self.assertEqual(fetched.json()["items"][0]["automation_id"], automation_id)


    def test_create_execution_persists_input_variables(self):
        automation_id = self._seed_published_automation()

        response = self.client.post(
            "/executions",
            json={
                "name": "Execution with inputs",
                "automation_ids": [automation_id],
                "inputs": {
                    "company": "001",
                    "period_start": "2026-10-01"
                },
                "test_mode": True,
            },
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(
            response.json()["inputs"],
            {"company": "001", "period_start": "2026-10-01"},
        )

        execution_id = response.json()["id"]
        db = self.session_factory()
        try:
            stored = db.get(Execution, execution_id)
            self.assertEqual(
                stored.inputs,
                {"company": "001", "period_start": "2026-10-01"},
            )
        finally:
            db.close()

    def test_execution_rejects_unpublished_automation(self):
        db = self.session_factory()
        try:
            automation = Automation(
                code="RASCUNHO",
                name="Rascunho",
                status=AutomationStatus.DRAFT.value,
                current_version=1,
            )
            db.add(automation)
            db.flush()
            db.add(
                AutomationVersion(
                    automation_id=automation.id,
                    version=1,
                    recipe={"version": 1, "steps": []},
                )
            )
            db.commit()
            automation_id = automation.id
        finally:
            db.close()

        response = self.client.post(
            "/executions",
            json={
                "name": "Inválida",
                "automation_ids": [automation_id],
            },
        )

        self.assertEqual(response.status_code, 409)
        self.assertEqual(
            response.json(),
            {
                "error": {
                    "code": "AUTOMATION_NOT_PUBLISHED",
                    "message": "Automation is not published",
                    "details": None,
                }
            },
        )

    def test_cancel_queued_execution(self):
        automation_id = self._seed_published_automation()

        created = self.client.post(
            "/executions",
            json={"name": "Cancelar", "automation_ids": [automation_id]},
        )
        execution_id = created.json()["id"]

        cancelled = self.client.post(f"/executions/{execution_id}/cancel")

        self.assertEqual(cancelled.status_code, 200)
        body = cancelled.json()
        self.assertEqual(body["status"], "CANCELLED")
        self.assertTrue(body["cancel_requested"])
        self.assertEqual(body["items"][0]["status"], "CANCELLED")

    def test_cancel_queued_execution_persists_event(self):
        automation_id = self._seed_published_automation()

        created = self.client.post(
            "/executions",
            json={"name": "Cancelar com evento", "automation_ids": [automation_id]},
        )
        execution_id = created.json()["id"]

        cancelled = self.client.post(f"/executions/{execution_id}/cancel")

        self.assertEqual(cancelled.status_code, 200)

        db = self.session_factory()
        try:
            events = list(
                db.query(Event)
                .filter(Event.execution_id == execution_id)
                .order_by(Event.id)
                .all()
            )
            self.assertEqual([event.type for event in events], ["execution.cancelled"])
            self.assertEqual(events[0].level, "INFO")
        finally:
            db.close()

    def test_list_executions_supports_status_filter_and_pagination(self):
        automation_id = self._seed_published_automation()
        for name in ("Uma", "Duas", "Três"):
            self.client.post(
                "/executions",
                json={"name": name, "automation_ids": [automation_id]},
            )

        response = self.client.get("/executions?status=QUEUED&limit=2&offset=1")

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["total"], 3)
        self.assertEqual(body["limit"], 2)
        self.assertEqual(body["offset"], 1)
        self.assertEqual(len(body["items"]), 2)


if __name__ == "__main__":
    unittest.main()
