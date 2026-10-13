import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

from alembic import command
from alembic.config import Config
from test_client import AuthenticatedTestClient as TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import get_db
from app.main import app


BACKEND_ROOT = Path(__file__).resolve().parents[1]


class AutomationVersionsApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        db_path = Path(cls.tmp.name) / "versions.db"

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
                "workers",
            ):
                db.execute(__import__("sqlalchemy").text(f"DELETE FROM {table}"))
            db.commit()
        finally:
            db.close()

    def _create_automation(self):
        response = self.client.post(
            "/automations",
            json={"code": "VERSAO1", "name": "Versão Teste"},
        )
        self.assertEqual(response.status_code, 201)
        return response.json()["id"]

    @staticmethod
    def _valid_recipe():
        return {
            "schema_version": 1,
            "name": "Receita v1",
            "variables": {},
            "steps": [
                {
                    "id": "open",
                    "action": "navigate",
                    "url": "https://example.test/report",
                }
            ],
            "output": {"type": "file"},
        }

    def test_option_preparation_is_ephemeral_and_requires_published_report(self):
        automation_id = self._create_automation()
        recipe = self._valid_recipe()
        self.client.post(f"/automations/{automation_id}/versions", json={"recipe": recipe})
        endpoint = f"/automations/{automation_id}/versions/1/input-options"
        with patch("app.api.automation_versions.read_options", return_value={"fields": {"company": {"options": [{"value": "live", "label": "Live company", "disabled": False}], "error": None}}}) as reader:
            self.assertEqual(self.client.post(endpoint, json={"inputs": {}}).status_code, 409)
            reader.assert_not_called()
            self.client.post(f"/automations/{automation_id}/versions/1/test")
            self.client.post(f"/automations/{automation_id}/versions/1/publish")
            response = self.client.post(endpoint, json={"inputs": {"company": "execution-only"}})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.headers["Cache-Control"], "no-store")
            reader.assert_called_once_with(recipe, {"company": "execution-only"})
        self.assertEqual(self.client.get(f"/automations/{automation_id}/versions/1").json()["recipe"], recipe)
        with self.session_factory() as db:
            self.assertEqual(db.execute(__import__("sqlalchemy").text("SELECT COUNT(*) FROM executions")).scalar(), 0)
        from app.models import Automation
        with self.session_factory() as db:
            db.get(Automation, automation_id).system = "SGIND"
            db.commit()
        with patch("app.api.automation_versions.read_options") as reader:
            response = self.client.post(endpoint, json={"inputs": {}})
            self.assertEqual(response.status_code, 409)
            self.assertEqual(response.json()["error"]["code"], "CORPORATE_AUTH_NOT_VALIDATED")
            reader.assert_not_called()

    def test_create_test_and_publish_version(self):
        automation_id = self._create_automation()

        created = self.client.post(
            f"/automations/{automation_id}/versions",
            json={"recipe": self._valid_recipe()},
        )

        self.assertEqual(created.status_code, 201)
        self.assertEqual(created.json()["version"], 1)
        self.assertIsNone(created.json()["test_status"])
        self.assertEqual(created.json()["published"], False)

        tested = self.client.post(
            f"/automations/{automation_id}/versions/1/test",
        )

        self.assertEqual(tested.status_code, 200)
        self.assertEqual(tested.json()["test_status"], "PASSED")

        published = self.client.post(
            f"/automations/{automation_id}/versions/1/publish",
        )

        self.assertEqual(published.status_code, 200)
        self.assertEqual(published.json()["published"], True)
        self.assertEqual(published.json()["automation_status"], "PUBLISHED")

        automation = self.client.get(f"/automations/{automation_id}")
        self.assertEqual(automation.json()["current_version"], 1)

    def test_publish_rejects_untested_version(self):
        automation_id = self._create_automation()

        self.assertEqual(
            self.client.post(
                f"/automations/{automation_id}/versions",
                json={"recipe": self._valid_recipe()},
            ).status_code,
            201,
        )

        response = self.client.post(
            f"/automations/{automation_id}/versions/1/publish",
        )

        self.assertEqual(response.status_code, 409)
        self.assertEqual(
            response.json()["error"]["code"],
            "AUTOMATION_VERSION_NOT_TESTED",
        )

    def test_invalid_recipe_fails_test(self):
        automation_id = self._create_automation()

        created = self.client.post(
            f"/automations/{automation_id}/versions",
            json={"recipe": {"schema_version": 1, "name": "Inválida"}},
        )
        self.assertEqual(created.status_code, 201)

        tested = self.client.post(
            f"/automations/{automation_id}/versions/1/test",
        )

        self.assertEqual(tested.status_code, 422)
        self.assertEqual(
            tested.json()["error"]["code"],
            "INVALID_RECIPE",
        )

    def test_runtime_invalid_recipes_cannot_pass_validation_or_be_published(self):
        invalid_steps = [
            [{"id": "script", "action": "run_python", "code": "synthetic"}],
            [{"id": "click", "action": "click"}],
            [{"id": "fill", "action": "fill", "selector": "#company", "value": "{{missing}}"}],
            [{"id": "duplicate", "action": "click", "selector": "#one"},
             {"id": "duplicate", "action": "click", "selector": "#two"}],
            [{"id": "retry", "action": "click", "selector": "#one", "retry": {"max_attempts": 6}}],
        ]
        automation_id = self._create_automation()
        for number, steps in enumerate(invalid_steps, start=1):
            with self.subTest(steps=steps):
                recipe = {**self._valid_recipe(), "steps": steps}
                created = self.client.post(f"/automations/{automation_id}/versions", json={"recipe": recipe})
                self.assertEqual(created.status_code, 201)
                tested = self.client.post(f"/automations/{automation_id}/versions/{number}/test")
                self.assertEqual(tested.status_code, 422)
                saved = self.client.get(f"/automations/{automation_id}/versions/{number}")
                self.assertEqual(saved.json()["test_status"], "FAILED")
                published = self.client.post(f"/automations/{automation_id}/versions/{number}/publish")
                self.assertEqual(published.status_code, 409)


if __name__ == "__main__":
    unittest.main()
