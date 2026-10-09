"""Synthetic credentials only: exercise submission, persistence and revocation."""
import tempfile
import unittest
from datetime import timedelta
from pathlib import Path
from unittest.mock import patch

from sqlalchemy import create_engine, select, func
from sqlalchemy.orm import sessionmaker
from test_client import AuthenticatedTestClient
from app.database import get_db
from app.models import Base
from app.main import app
from app.models import Automation, AutomationVersion, Execution, Worker, utcnow
from app.security import credential_vault, SESSION_COOKIE_NAME, revoke_session
from app.worker_channel import worker_channel
from app.api import executions


class ExecutionCredentialsTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue(hasattr(executions, "require_validated_corporate_auth"),
                        "Submission lacks the trusted adapter gate and ephemeral binding")
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "synthetic.db"
        self.engine = create_engine(f"sqlite:///{self.path}", connect_args={"check_same_thread": False})
        Base.metadata.create_all(self.engine)
        self.factory = sessionmaker(bind=self.engine)
        def db_override():
            with self.factory() as db:
                yield db
        app.dependency_overrides[get_db] = db_override
        # This approval exists only in tests, never in a request or configuration.
        app.dependency_overrides[executions.require_validated_corporate_auth] = lambda: None
        worker_channel.configure("synthetic-worker", "synthetic-capability")
        self.client = AuthenticatedTestClient(app)
        self.owner = self.client.cookies.get(SESSION_COOKIE_NAME)
        with self.factory() as db:
            automation = Automation(code="SYNTHETIC", name="Synthetic", system="SGIND",
                                    status="PUBLISHED", current_version=1)
            db.add(automation)
            db.flush()
            self.automation_id = automation.id
            db.add(AutomationVersion(automation_id=automation.id, version=1,
                                     recipe={"version": 1, "steps": []}))
            db.add(Worker(worker_id="synthetic-worker", status="ONLINE",
                          heartbeat_at=utcnow(), started_at=utcnow()))
            db.commit()
        self.lookup = patch.object(worker_channel, "_lookup", self.lookup_execution)
        self.lookup.start()
        self.payload = {"name": "Synthetic", "automation_ids": [self.automation_id],
                        "inputs": {"company": "001"},
                        "corporate_credentials": {"SGIND": {"username": "canary-user-482",
                                                            "password": "canary-password-482"}}}

    def lookup_execution(self, execution_id):
        with self.factory() as db:
            return db.get(Execution, execution_id)

    def tearDown(self):
        if not hasattr(self, "client"):
            return
        revoke_session(self.owner)
        worker_channel.configure("after-test", "after-test-capability")
        self.lookup.stop()
        self.client.close()
        app.dependency_overrides.clear()
        self.engine.dispose()
        self.tmp.cleanup()

    def create(self):
        response = self.client.post("/executions", json=self.payload)
        self.assertEqual(response.status_code, 201, response.text)
        return response

    def assert_empty(self):
        with self.factory() as db:
            self.assertEqual(db.scalar(select(func.count()).select_from(Execution)), 0)
        with self.assertRaisesRegex(RuntimeError, "^CREDENTIALS_UNAVAILABLE$"):
            credential_vault.get(1, self.owner, "SGIND")

    def test_submission_binds_only_memory_and_requires_worker_claim(self):
        response = self.create()
        execution_id = response.json()["id"]
        self.assertNotIn("canary", response.text)
        self.assertNotIn(self.owner, response.text)
        self.assertEqual(response.json()["inputs"], {"company": "001"})
        with self.engine.connect() as connection:
            dump = "\n".join(connection.connection.driver_connection.iterdump())
        self.assertNotIn("canary", dump)
        self.assertNotIn(self.owner, dump)
        with self.assertRaises(RuntimeError):
            worker_channel.resolve(execution_id, "SGIND", "synthetic-capability")
        with self.factory() as db:
            execution = db.get(Execution, execution_id)
            execution.worker_id = "synthetic-worker"
            execution.status = "RUNNING"
            db.commit()
        self.assertEqual(worker_channel.resolve(execution_id, "SGIND", "synthetic-capability"),
                         self.payload["corporate_credentials"]["SGIND"])
        worker_channel.release(execution_id, "synthetic-capability")
        worker_channel.release(execution_id, "synthetic-capability")
        with self.assertRaises(RuntimeError):
            credential_vault.get(execution_id, self.owner, "SGIND")

    def test_cancel_revokes_before_claim(self):
        execution_id = self.create().json()["id"]
        self.assertEqual(credential_vault.get(execution_id, self.owner, "SGIND")["password"],
                         "canary-password-482")
        response = self.client.post(f"/executions/{execution_id}/cancel")
        self.assertEqual(response.status_code, 200)
        with self.assertRaises(RuntimeError):
            credential_vault.get(execution_id, self.owner, "SGIND")

    def test_logout_revokes_submission(self):
        execution_id = self.create().json()["id"]
        self.assertEqual(credential_vault.get(execution_id, self.owner, "SGIND")["password"],
                         "canary-password-482")
        self.assertEqual(self.client.post("/auth/logout").status_code, 200)
        with self.assertRaises(RuntimeError):
            credential_vault.get(execution_id, self.owner, "SGIND")

    def test_commit_failure_rolls_back_and_revokes(self):
        from sqlalchemy.exc import IntegrityError
        def fail_commit(db):
            self.assertEqual(credential_vault.get(1, self.owner, "SGIND")["password"],
                             "canary-password-482")
            raise IntegrityError("synthetic", {}, Exception("synthetic"))
        with patch.object(self.factory.class_, "commit", autospec=True, side_effect=fail_commit):
            response = self.client.post("/executions", json=self.payload)
        self.assertEqual(response.status_code, 409)
        self.assertNotIn("canary", response.text)
        self.assert_empty()

    def test_stale_worker_rejected_before_publication(self):
        with self.factory() as db:
            worker = db.scalar(select(Worker))
            worker.heartbeat_at = utcnow() - timedelta(minutes=5)
            db.commit()
        response = self.client.post("/executions", json=self.payload)
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["error"]["code"], "CREDENTIALS_UNAVAILABLE")
        self.assert_empty()

    def test_foreign_system_rejected_without_storing(self):
        self.payload["corporate_credentials"]["IQOS"] = self.payload["corporate_credentials"].pop("SGIND")
        response = self.client.post("/executions", json=self.payload)
        self.assertEqual(response.status_code, 422)
        self.assert_empty()

    def test_session_expiry_bounds_vault_ttl(self):
        import app.security as security
        with security._sessions_lock:
            username, _ = security._sessions[self.owner]
            security._sessions[self.owner] = (username, security.time.monotonic() + 20)
        execution_id = self.create().json()["id"]
        self.assertEqual(credential_vault.get(execution_id, self.owner, "SGIND")["password"],
                         "canary-password-482")
        with patch.object(credential_vault, "_clock", return_value=security.time.monotonic() + 21):
            with self.assertRaises(RuntimeError):
                credential_vault.get(execution_id, self.owner, "SGIND")

    def test_default_gate_remains_blocked(self):
        del app.dependency_overrides[executions.require_validated_corporate_auth]
        response = self.client.post("/executions", json=self.payload)
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["error"]["code"], "CORPORATE_AUTH_NOT_VALIDATED")
        self.assert_empty()


    def test_unconfigured_channel_rejected_without_storing(self):
        with patch.object(worker_channel, "_capability", None):
            response = self.client.post("/executions", json=self.payload)
        self.assertEqual(response.status_code, 409)
        self.assert_empty()

    def test_incarnation_change_during_submission_revokes_and_rolls_back(self):
        original_bind = worker_channel.bind
        def changed_bind(execution_id, owner, **kwargs):
            worker_channel.configure("replacement-worker", "replacement-capability")
            return original_bind(execution_id, owner, **kwargs)
        with patch.object(worker_channel, "bind", side_effect=changed_bind):
            response = self.client.post("/executions", json=self.payload)
        self.assertEqual(response.status_code, 409)
        self.assert_empty()

    def test_logout_between_authorization_and_store_rejects_submission(self):
        original_bind = executions.bind_execution_credentials
        def logged_out(execution_id, owner, systems, db):
            revoke_session(owner)
            return original_bind(execution_id, owner, systems, db)
        with patch.object(executions, "bind_execution_credentials", side_effect=logged_out):
            response = self.client.post("/executions", json=self.payload)
        self.assertEqual(response.status_code, 409)
        self.assert_empty()

    def test_unexpected_commit_failure_also_revokes(self):
        def fail_commit(db):
            self.assertEqual(credential_vault.get(1, self.owner, "SGIND")["password"],
                             "canary-password-482")
            raise RuntimeError("synthetic-database-failure")
        with patch.object(self.factory.class_, "commit", autospec=True, side_effect=fail_commit):
            with self.assertRaisesRegex(RuntimeError, "synthetic-database-failure"):
                self.client.post("/executions", json=self.payload)
        self.assert_empty()
