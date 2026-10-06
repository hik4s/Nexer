import json
import tempfile
import unittest
from pathlib import Path

from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.database import get_db
from app.enums import ExecutionStatus
from app.main import app
from app.models import Event, Execution


BACKEND_ROOT = Path(__file__).resolve().parents[1]


class EventsSseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        db_path = Path(cls.tmp.name) / "relatpy.db"

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

    def _seed_execution(self):
        db = self.session_factory()
        try:
            execution = Execution(
                name="SSE",
                status=ExecutionStatus.SUCCEEDED.value,
                send_to_network=False,
                keep_local_copy=True,
                overwrite_existing=False,
                test_mode=True,
                cancel_requested=False,
            )
            db.add(execution)
            db.flush()
            db.add_all(
                [
                    Event(
                        execution_id=execution.id,
                        type="execution.created",
                        level="INFO",
                        message="Execution created",
                        payload={"stage": "CREATED"},
                    ),
                    Event(
                        execution_id=execution.id,
                        type="execution.finished",
                        level="INFO",
                        message="Execution finished",
                        payload={"status": "SUCCEEDED"},
                    ),
                ]
            )
            db.commit()
            return execution.id
        finally:
            db.close()

    def test_events_endpoint_returns_sse_stream(self):
        execution_id = self._seed_execution()

        response = self.client.get(f"/executions/{execution_id}/events")

        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            response.headers["content-type"].startswith("text/event-stream")
        )
        self.assertIn("event: execution.created", response.text)
        self.assertIn("event: execution.finished", response.text)
        self.assertIn('data: {"stage": "CREATED"}', response.text)

    def test_last_event_id_skips_already_received_events(self):
        execution_id = self._seed_execution()

        db = self.session_factory()
        try:
            first_id = db.execute(
                text(
                    "SELECT id FROM events "
                    "WHERE execution_id = :execution_id "
                    "ORDER BY id LIMIT 1"
                ),
                {"execution_id": execution_id},
            ).scalar_one()
        finally:
            db.close()

        response = self.client.get(
            f"/executions/{execution_id}/events",
            headers={"Last-Event-ID": str(first_id)},
        )

        self.assertEqual(response.status_code, 200)
        self.assertNotIn("event: execution.created", response.text)
        self.assertIn("event: execution.finished", response.text)

    def test_missing_execution_returns_standard_error(self):
        response = self.client.get("/executions/999999/events")

        self.assertEqual(response.status_code, 404)
        self.assertEqual(
            response.json(),
            {
                "error": {
                    "code": "EXECUTION_NOT_FOUND",
                    "message": "Execution not found",
                    "details": None,
                }
            },
        )


if __name__ == "__main__":
    unittest.main()
