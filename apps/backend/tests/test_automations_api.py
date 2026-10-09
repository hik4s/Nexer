import tempfile
import unittest
from pathlib import Path

from alembic import command
from alembic.config import Config
from test_client import AuthenticatedTestClient as TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import get_db
from app.main import app


BACKEND_ROOT = Path(__file__).resolve().parents[1]


class AutomationsApiTests(unittest.TestCase):
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


    def setUp(self):
        db = self.session_factory()
        try:
            for table in ("events", "artifacts", "checkpoints", "execution_automations"):
                db.execute(__import__("sqlalchemy").text(f"DELETE FROM {table}"))
            for table in ("executions", "automation_versions", "destinations", "automations"):
                db.execute(__import__("sqlalchemy").text(f"DELETE FROM {table}"))
            db.commit()
        finally:
            db.close()

    @classmethod
    def tearDownClass(cls):
        app.dependency_overrides.clear()
        cls.engine.dispose()
        cls.tmp.cleanup()

    def test_create_and_list_automation(self):
        created = self.client.post(
            "/automations",
            json={
                "code": "RECLAMACOES",
                "name": "Reclamações",
                "description": "Automação piloto",
                "system": "SGIND",
            },
        )

        self.assertEqual(created.status_code, 201)
        created_body = created.json()
        self.assertEqual(created_body["code"], "RECLAMACOES")
        self.assertEqual(created_body["name"], "Reclamações")
        self.assertEqual(created_body["status"], "DRAFT")
        self.assertIsNone(created_body["current_version"])
        self.assertNotIn("path_reference", created_body)

        listed = self.client.get("/automations?limit=10&offset=0")

        self.assertEqual(listed.status_code, 200)
        body = listed.json()
        self.assertEqual(body["total"], 1)
        self.assertEqual(body["limit"], 10)
        self.assertEqual(body["offset"], 0)
        self.assertEqual(body["items"][0]["code"], "RECLAMACOES")

    def test_duplicate_code_returns_standard_conflict_error(self):
        payload = {"code": "UNICA", "name": "Primeira"}

        first = self.client.post("/automations", json=payload)
        second = self.client.post("/automations", json=payload)

        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 409)
        self.assertEqual(
            second.json(),
            {
                "error": {
                    "code": "AUTOMATION_CODE_EXISTS",
                    "message": "Automation code already exists",
                    "details": None,
                }
            },
        )

    def test_filter_by_status(self):
        self.client.post(
            "/automations",
            json={"code": "DRAFT01", "name": "Rascunho"},
        )
        self.client.post(
            "/automations",
            json={"code": "DRAFT02", "name": "Outro"},
        )

        response = self.client.get("/automations?status=DRAFT")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["total"], 2)
        self.assertTrue(
            all(item["status"] == "DRAFT" for item in response.json()["items"])
        )


if __name__ == "__main__":
    unittest.main()
