import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.database import get_db
from app.enums import WorkerStatus
from app.main import app
from app.models import Automation, AutomationVersion, Worker


BACKEND_ROOT = Path(__file__).resolve().parents[1]


class DiagnosticsApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        db_path = Path(cls.tmp.name) / "diagnostics.db"

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
            db.execute(text("DELETE FROM workers"))
            db.commit()
            db.add(
                Worker(
                    worker_id="diag-worker",
                    status=WorkerStatus.ONLINE.value,
                    hostname="diag-host",
                    pid=123,
                    concurrency_limit=2,
                    current_load=1,
                    heartbeat_at=datetime.now(timezone.utc).replace(tzinfo=None),
                    started_at=datetime.now(timezone.utc).replace(tzinfo=None),
                )
            )
            db.commit()
        finally:
            db.close()

    def test_diagnostics_reports_database_and_workers(self):
        response = self.client.get("/diagnostics")

        self.assertEqual(response.status_code, 200)
        body = response.json()

        self.assertEqual(body["status"], "ok")
        self.assertEqual(body["database"]["status"], "ok")
        self.assertEqual(body["workers"]["online"], 1)
        self.assertEqual(body["workers"]["total"], 1)

    def test_diagnostics_reports_authentication_configuration_without_secrets(self):
        db = self.session_factory()
        try:
            automation = Automation(code="AUTH-DIAG", name="Auth diagnostics")
            db.add(automation)
            db.flush()
            db.add_all(
                [
                    AutomationVersion(
                        automation_id=automation.id,
                        version=1,
                        recipe={
                            "schema_version": 1,
                            "name": "With auth",
                            "authentication": {
                                "session_ref": "portal-a",
                                "login_selectors": ["#login"],
                            },
                            "steps": [],
                            "output": {"type": "file"},
                        },
                    ),
                    AutomationVersion(
                        automation_id=automation.id,
                        version=2,
                        recipe={
                            "schema_version": 1,
                            "name": "With renewal",
                            "authentication": {
                                "session_ref": "portal-b",
                                "login_selectors": ["#login"],
                                "renewal": {
                                    "login_url": "https://example.test/login",
                                    "username_selector": "#user",
                                    "password_selector": "#pass",
                                    "submit_selector": "#submit",
                                    "success_selector": "#logout",
                                    "username_ref": "portal.username",
                                    "password_ref": "portal.password",
                                },
                            },
                            "steps": [],
                            "output": {"type": "file"},
                        },
                    ),
                ]
            )
            db.commit()
        finally:
            db.close()

        response = self.client.get("/diagnostics")

        self.assertEqual(response.status_code, 200)
        authentication = response.json()["authentication"]
        self.assertEqual(authentication["configured"], 2)
        self.assertEqual(authentication["renewal_configured"], 1)
        self.assertNotIn("portal.username", response.text)
        self.assertNotIn("portal.password", response.text)


if __name__ == "__main__":
    unittest.main()
