import tempfile
import unittest
from pathlib import Path
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from test_client import AuthenticatedTestClient
from app.database import get_db
from app.main import app

class LoginProfileApiTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        url = "sqlite:///" + str(Path(self.tmp.name) / "profiles.db")
        config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
        config.set_main_option("sqlalchemy.url", url)
        command.upgrade(config, "head")
        self.engine = create_engine(url, connect_args={"check_same_thread": False})
        self.factory = sessionmaker(bind=self.engine)
        def override():
            with self.factory() as db: yield db
        app.dependency_overrides[get_db] = override
        self.client = AuthenticatedTestClient(app)
    def tearDown(self):
        self.client.close(); app.dependency_overrides.clear(); self.engine.dispose(); self.tmp.cleanup()
    def test_profile_versions_have_configuration_only_and_are_immutable(self):
        created = self.client.post("/login-profiles", json={"name": "Site local", "login_url": "http://127.0.0.1:8765/login"})
        self.assertEqual(created.status_code, 201)
        profile = created.json(); pid = profile["id"]
        self.assertEqual(profile["status"], "DRAFT")
        self.assertEqual(profile["current_version"], 1)
        configuration = profile["configuration"]
        for key, selector in (("username_target", "#user"), ("password_target", "#pass"), ("submit_target", "#submit")):
            configuration[key] = {"selector": selector, "frames": []}
        configuration["success_rule"] = {"kind": "marker", "target": {"selector": "#home", "frames": []}}
        version = self.client.post(f"/login-profiles/{pid}/versions", json=configuration)
        self.assertEqual(version.status_code, 201)
        self.assertEqual(version.json()["current_version"], 2)
        self.assertEqual(self.client.get(f"/login-profiles/{pid}/versions/1").json()["configuration"]["username_target"], None)
        ready = self.client.post(f"/login-profiles/{pid}/publish", json={"version": 2})
        self.assertEqual(ready.status_code, 200)
        self.assertEqual(ready.json()["status"], "READY")
        self.assertEqual(self.client.get("/login-profiles").json()["items"][0]["id"], pid)
        self.assertEqual(self.client.delete(f"/login-profiles/{pid}").status_code, 200)
        self.assertEqual(self.client.get(f"/login-profiles/{pid}/versions/2").status_code, 200)
    def test_secret_payload_and_untrusted_urls_never_enter_profile(self):
        for url in ("http://example.com/login", "https://user:secret@site.invalid/login", "https://site.invalid/login?token=canary"):
            self.assertEqual(self.client.post("/login-profiles", json={"name": "Bad", "login_url": url}).status_code, 422)
        response = self.client.post("/login-profiles", json={"name": "Bad", "login_url": "https://site.invalid/login", "password": "private-canary"})
        self.assertEqual(response.status_code, 422)
        self.assertNotIn("private-canary", response.text)
        profile = self.client.post("/login-profiles", json={"name": "Draft", "login_url": "https://site.invalid/login"}).json()
        self.assertEqual(self.client.post(f"/login-profiles/{profile['id']}/publish", json={"version": 1}).status_code, 422)

    def test_invalid_login_url_explains_requirements_without_echoing_input(self):
        for url in ("http://example.com/login", "https://site.invalid/login?token=url-private-canary", "https://user:url-private-canary@site.invalid/login"):
            with self.subTest(url_kind=url.split(":", 1)[0]):
                response = self.client.post("/login-profiles", json={"name": "Site", "login_url": url})
                self.assertEqual(response.status_code, 422)
                error = response.json()["error"]
                self.assertEqual(error["code"], "LOGIN_URL_INVALID")
                self.assertIn("HTTPS", error["message"])
                self.assertIn("parâmetros", error["message"])
                self.assertNotIn("url-private-canary", response.text)
                self.assertNotIn(url, response.text)
        self.assertEqual(self.client.get("/login-profiles").json()["total"], 0)

    def test_corporate_picker_starts_without_publishing_profile_or_logging_in(self):
        import io
        from unittest.mock import Mock, patch
        from app.services.login_recordings import login_recordings
        profile = self.client.post("/login-profiles", json={
            "name": "SGIND", "login_url": "https://indicadoresenergisaess.scl.corp/sgind/",
        }).json()
        process = Mock(stdin=io.StringIO(), stdout=io.StringIO())
        process.poll.return_value = 0
        try:
            with patch.object(login_recordings, "_start_process", return_value=process):
                response = self.client.post(f"/login-profiles/{profile['id']}/recordings")
            self.assertEqual(response.status_code, 201)
            self.assertEqual(response.json()["profile_id"], profile["id"])
            self.assertEqual(self.client.get(f"/login-profiles/{profile['id']}").json()["status"], "DRAFT")
            self.assertEqual(self.client.get("/executions").json()["total"], 0)
        finally:
            login_recordings.close_all()

    def test_profile_execution_requires_ephemeral_credentials_not_recipe_inputs(self):
        profile = self.client.post("/login-profiles", json={"name": "Local", "login_url": "http://127.0.0.1:8765/login"}).json()
        configuration = profile["configuration"]
        for key, selector in (("username_target", "#user"), ("password_target", "#pass"), ("submit_target", "#submit")):
            configuration[key] = {"selector": selector, "frames": []}
        configuration["success_rule"] = {"kind": "url", "url": "http://127.0.0.1:8765/home"}
        self.client.post(f"/login-profiles/{profile['id']}/versions", json=configuration)
        self.client.post(f"/login-profiles/{profile['id']}/publish", json={"version": 2})
        automation = self.client.post("/automations", json={"code": "PROFILE", "name": "Flow"}).json()
        recipe = {"schema_version": 1, "name": "Flow", "variables": {}, "login_profile": {"id": profile["id"], "version": 2}, "steps": [{"id": "open", "action": "navigate", "url": "http://127.0.0.1:8765/home"}], "output": {"type": "file"}}
        self.client.post(f"/automations/{automation['id']}/versions", json={"recipe": recipe})
        self.client.post(f"/automations/{automation['id']}/versions/1/test")
        self.client.post(f"/automations/{automation['id']}/versions/1/publish")
        response = self.client.post("/executions", json={"name": "Missing", "automation_ids": [automation["id"]]})
        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json()["error"]["code"], "PROFILE_CREDENTIALS_REQUIRED")
        dry_run = self.client.post("/executions", json={"name": "Dry", "automation_ids": [automation["id"]], "test_mode": True})
        self.assertEqual(dry_run.status_code, 201)
        self.assertEqual(dry_run.json()["inputs"], {})
        from unittest.mock import patch
        from app.models import Worker, Execution, utcnow
        from app.worker_channel import worker_channel
        import json
        worker_channel.configure("profile-worker", "synthetic-profile-capability")
        with self.factory() as db:
            db.add(Worker(worker_id="profile-worker", status="ONLINE", concurrency_limit=1, current_load=0, heartbeat_at=utcnow(), started_at=utcnow(), created_at=utcnow()))
            db.commit()
        def lookup(execution_id):
            with self.factory() as db: return db.get(Execution, execution_id)
        identity = f"profile-{profile['id']}-v2"
        with patch.object(worker_channel, "_lookup", side_effect=lookup):
            created = self.client.post("/executions", json={"name": "Private", "automation_ids": [automation["id"]], "profile_credentials": {identity: {"username": "user-canary", "password": "private-password-canary"}}})
            self.assertEqual(created.status_code, 201)
            execution_id = created.json()["id"]
            self.assertNotIn("private-password-canary", created.text)
            with self.factory() as db:
                stored = db.get(Execution, execution_id)
                self.assertNotIn("private-password-canary", json.dumps({"inputs": stored.inputs, "profiles": stored.login_profiles}))
                stored.status = "RUNNING"; stored.worker_id = "profile-worker"; db.commit()
            self.assertEqual(worker_channel.resolve(execution_id, identity, "synthetic-profile-capability")["password"], "private-password-canary")
            worker_channel.revoke(execution_id)
            with self.assertRaises(RuntimeError): worker_channel.resolve(execution_id, identity, "synthetic-profile-capability")

