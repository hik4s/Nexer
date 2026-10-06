import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.database import get_db
from app.enums import WorkerStatus
from app.main import app
from app.models import Worker


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
                    heartbeat_at=datetime.utcnow(),
                    started_at=datetime.utcnow(),
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


if __name__ == "__main__":
    unittest.main()
