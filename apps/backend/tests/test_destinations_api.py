import tempfile
import unittest
from pathlib import Path

from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.database import get_db
from app.main import app


BACKEND_ROOT = Path(__file__).resolve().parents[1]


class DestinationsApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        db_path = Path(cls.tmp.name) / "destinations.db"

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

    def setUp(self):
        db = self.session_factory()
        try:
            db.execute(text("DELETE FROM destinations"))
            db.commit()
        finally:
            db.close()

    def test_create_and_list_destination(self):
        response = self.client.post(
            "/destinations",
            json={
                "code": "LOCAL_REPORTS",
                "name": "Relatórios locais",
                "path_reference": "C:/RelatPy/outputs",
            },
        )

        self.assertEqual(response.status_code, 201)
        self.assertTrue(response.json()["enabled"])

        listed = self.client.get("/destinations")
        self.assertEqual(listed.status_code, 200)
        self.assertEqual(listed.json()["total"], 1)
        self.assertEqual(listed.json()["items"][0]["code"], "LOCAL_REPORTS")

    def test_duplicate_code_returns_conflict(self):
        payload = {
            "code": "NETWORK_REPORTS",
            "name": "Relatórios de rede",
            "path_reference": r"\\server\reports",
        }

        self.assertEqual(self.client.post("/destinations", json=payload).status_code, 201)
        response = self.client.post("/destinations", json=payload)

        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["error"]["code"], "DESTINATION_CODE_CONFLICT")

    def test_blank_path_is_rejected(self):
        response = self.client.post(
            "/destinations",
            json={
                "code": "INVALID",
                "name": "Inválido",
                "path_reference": "   ",
            },
        )

        self.assertEqual(response.status_code, 422)


if __name__ == "__main__":
    unittest.main()
