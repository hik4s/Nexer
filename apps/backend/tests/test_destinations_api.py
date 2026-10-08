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

    def test_update_destination(self):
        created = self.client.post(
            "/destinations",
            json={
                "code": "LOCAL",
                "name": "Local",
                "path_reference": "C:/old",
            },
        ).json()

        response = self.client.put(
            f"/destinations/{created['id']}",
            json={
                "code": "LOCAL_UPDATED",
                "name": "Local atualizado",
                "path_reference": "C:/new",
                "enabled": False,
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["code"], "LOCAL_UPDATED")
        self.assertFalse(response.json()["enabled"])

    def test_update_rejects_duplicate_code(self):
        first = {
            "code": "FIRST",
            "name": "Primeiro",
            "path_reference": "C:/first",
        }
        second = {
            "code": "SECOND",
            "name": "Segundo",
            "path_reference": "C:/second",
        }

        self.client.post("/destinations", json=first)
        created = self.client.post("/destinations", json=second).json()

        response = self.client.put(
            f"/destinations/{created['id']}",
            json={**second, "code": "FIRST"},
        )

        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["error"]["code"], "DESTINATION_CODE_CONFLICT")

    def test_delete_destination(self):
        created = self.client.post(
            "/destinations",
            json={
                "code": "DELETE_ME",
                "name": "Excluir",
                "path_reference": "C:/delete",
            },
        ).json()

        response = self.client.delete(f"/destinations/{created['id']}")

        self.assertEqual(response.status_code, 204)
        self.assertEqual(
            self.client.get(f"/destinations/{created['id']}").status_code,
            404,
        )


if __name__ == "__main__":
    unittest.main()
