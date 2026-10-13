import tempfile
import unittest
from pathlib import Path

from alembic import command
from alembic.config import Config
from test_client import AuthenticatedTestClient as TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.database import get_db
from app.main import app
from app.models import Automation, AutomationVersion


BACKEND_ROOT = Path(__file__).resolve().parents[1]


class ExecutionSecretPolicyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        db_path = Path(cls.tmp.name) / "secret-policy.db"

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
            db.execute(text("DELETE FROM execution_automations"))
            db.execute(text("DELETE FROM executions"))
            db.execute(text("DELETE FROM automation_versions"))
            db.execute(text("DELETE FROM automations"))
            automation = Automation(
                code="SECRET_POLICY",
                name="Secret policy",
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
                        "name": "Secret policy",
                        "variables": {
                            "username": {
                                "type": "string",
                                "required": True,
                                "secret": False,
                            },
                            "password": {
                                "type": "string",
                                "required": True,
                                "secret": True,
                            },
                        },
                        "steps": [
                            {
                                "id": "open",
                                "action": "navigate",
                                "url": "https://example.test",
                            }
                        ],
                        "output": {"type": "file"},
                    },
                    test_status="PASSED",
                )
            )
            db.commit()
            self.automation_id = automation.id
        finally:
            db.close()

    def test_create_execution_rejects_inline_secret(self):
        response = self.client.post(
            "/executions",
            json={
                "name": "Não salvar segredo",
                "automation_ids": [self.automation_id],
                "inputs": {
                    "username": "user",
                    "password": "super-secret",
                },
                "test_mode": True,
            },
        )

        self.assertEqual(response.status_code, 422)
        self.assertEqual(
            response.json()["error"]["code"],
            "SECRET_INPUT_FORBIDDEN",
        )
        self.assertNotIn("super-secret", response.text)

    def test_create_execution_accepts_credential_reference(self):
        response = self.client.post(
            "/executions",
            json={
                "name": "Referência segura",
                "automation_ids": [self.automation_id],
                "inputs": {
                    "username": "user",
                    "password": {
                        "credential_ref": "nexer/sgind/password",
                    },
                },
                "test_mode": True,
            },
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(
            response.json()["inputs"]["password"]["credential_ref"],
            "nexer/sgind/password",
        )


if __name__ == "__main__":
    unittest.main()
