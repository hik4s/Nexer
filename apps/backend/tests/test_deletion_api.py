"""Safe deletion contract: no running jobs, no physical file deletion, no dangling rows."""
import tempfile
import unittest
from pathlib import Path

from sqlalchemy import create_engine, select, func
from sqlalchemy.orm import sessionmaker

from app.database import get_db
from app.main import app
from app.models import (Base, AccessGroup, Artifact, Automation, AutomationVersion,
                        Checkpoint, Event, Execution, ExecutionAutomation, ExecutionBatch,
                        LoginProfile, Routine)
from test_client import AuthenticatedTestClient


class DeletionApiTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.engine = create_engine("sqlite:///" + str(Path(self.tmp.name) / "test.db"),
                                    connect_args={"check_same_thread": False})
        Base.metadata.create_all(self.engine)
        self.factory = sessionmaker(bind=self.engine)
        def override():
            with self.factory() as db:
                yield db
        app.dependency_overrides[get_db] = override
        self.client = AuthenticatedTestClient(app)

    def tearDown(self):
        self.client.close()
        app.dependency_overrides.clear()
        self.engine.dispose()
        self.tmp.cleanup()

    def flow(self, code="SAFE_FLOW"):
        with self.factory() as db:
            flow = Automation(code=code, name=code, status="PUBLISHED", current_version=1)
            db.add(flow); db.flush()
            db.add(AutomationVersion(automation_id=flow.id, version=1, recipe={"steps": []}))
            identity = flow.id
            db.commit()
        return identity

    def execution(self, flow_id, *, status="SUCCEEDED", batch_id=None):
        with self.factory() as db:
            execution = Execution(name="Synthetic", status=status, batch_id=batch_id)
            db.add(execution); db.flush()
            item = ExecutionAutomation(execution_id=execution.id, automation_id=flow_id,
                                       automation_version=1, status="SUCCEEDED", stage="FINISHED")
            db.add(item); db.flush()
            db.add(Event(execution_id=execution.id, execution_automation_id=item.id,
                         type="test", level="INFO", message="synthetic"))
            db.add(Checkpoint(execution_automation_id=item.id, step_id="step",
                              step_index=0, status="SUCCEEDED"))
            db.add(Artifact(execution_automation_id=item.id, type="FILE",
                            filename="report.csv", local_path=str(Path(self.tmp.name) / "report.csv")))
            ids = execution.id, item.id
            db.commit()
        return ids

    def test_unused_flow_is_deleted_with_versions(self):
        identity = self.flow()
        response = self.client.delete(f"/automations/{identity}")
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json(), {"archived": False})
        self.assertEqual(self.client.get(f"/automations/{identity}").status_code, 404)
        with self.factory() as db:
            self.assertEqual(db.scalar(select(func.count()).select_from(AutomationVersion)), 0)
        self.assertEqual(self.client.delete(f"/automations/{identity}").status_code, 404)

    def test_flow_with_history_is_archived_and_records_remain(self):
        identity = self.flow()
        execution_id, _ = self.execution(identity)
        result = self.client.delete(f"/automations/{identity}")
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.json(), {"archived": True})
        self.assertEqual(self.client.get(f"/automations/{identity}").json()["status"], "ARCHIVED")
        self.assertEqual(self.client.get(f"/executions/{execution_id}").status_code, 200)

    def test_flow_cannot_be_removed_during_execution(self):
        identity = self.flow()
        execution_id, _ = self.execution(identity, status="RUNNING")
        result = self.client.delete(f"/automations/{identity}")
        self.assertEqual(result.status_code, 409, result.text)
        self.assertEqual(result.json()["error"]["code"], "AUTOMATION_IN_USE")
        self.assertEqual(self.client.get(f"/automations/{identity}").json()["status"], "PUBLISHED")
        with self.factory() as db:
            db.get(Execution, execution_id).status = "FAILED"
            db.commit()
        self.assertTrue(self.client.delete(f"/automations/{identity}").json()["archived"])

    def test_flow_referenced_by_routine_is_archived_without_history(self):
        identity = self.flow()
        with self.factory() as db:
            db.add(Routine(name="Reusable", items=[{"automation_id": identity, "version": 1, "inputs": {}}]))
            db.commit()
        response = self.client.delete(f"/automations/{identity}")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["archived"])

    def test_execution_requires_terminal_status_and_deletes_only_records(self):
        identity = self.flow()
        execution_id, _ = self.execution(identity, status="RUNNING")
        self.assertEqual(self.client.delete(f"/executions/{execution_id}").status_code, 409)
        output = Path(self.tmp.name) / "report.csv"
        output.write_text("not a real report")
        with self.factory() as db:
            db.get(Execution, execution_id).status = "SUCCEEDED"
            db.commit()
        self.assertEqual(self.client.delete(f"/executions/{execution_id}").status_code, 204)
        self.assertTrue(output.is_file())
        with self.factory() as db:
            for model in (Execution, ExecutionAutomation, Event, Checkpoint, Artifact):
                self.assertEqual(db.scalar(select(func.count()).select_from(model)), 0, model)
        self.assertEqual(self.client.delete(f"/executions/{execution_id}").status_code, 404)

    def test_batch_requires_all_finished_and_owns_deletion_of_its_executions(self):
        flow_id = self.flow()
        from hashlib import sha256
        # Batch owner must match the authenticated client's pairing session cookie.
        from app.security import SESSION_COOKIE_NAME
        token = self.client.cookies.get(SESSION_COOKIE_NAME)
        self.assertTrue(token)
        with self.factory() as db:
            batch = ExecutionBatch(name="Batch", owner_key=sha256(token.encode()).hexdigest(),
                                   idempotency_key="only-this-test", fingerprint="synthetic")
            db.add(batch); db.flush()
            batch_id = batch.id
            db.commit()
        first, _ = self.execution(flow_id, status="SUCCEEDED", batch_id=batch_id)
        second, _ = self.execution(flow_id, status="QUEUED", batch_id=batch_id)
        self.assertEqual(self.client.delete(f"/executions/{first}").status_code, 409)
        self.assertEqual(self.client.delete(f"/execution-batches/{batch_id}").status_code, 409)
        with self.factory() as db:
            db.get(Execution, second).status = "CANCELLED"
            db.commit()
        self.assertEqual(self.client.delete(f"/execution-batches/{batch_id}").status_code, 204)
        self.assertEqual(self.client.get(f"/execution-batches/{batch_id}").status_code, 404)
        with self.factory() as db:
            for model in (Execution, ExecutionAutomation, Event, Artifact, Checkpoint, ExecutionBatch):
                self.assertEqual(db.scalar(select(func.count()).select_from(model)), 0, model)

    def test_group_requires_unlinking_profiles(self):
        with self.factory() as db:
            group = AccessGroup(name="Example")
            db.add(group); db.flush()
            profile = LoginProfile(name="Site", group_id=group.id, current_version=1)
            db.add(profile); db.flush()
            group_id, profile_id = group.id, profile.id
            db.commit()
        self.assertEqual(self.client.delete(f"/access-groups/{group_id}").status_code, 409)
        with self.factory() as db:
            db.get(LoginProfile, profile_id).group_id = None
            db.commit()
        self.assertEqual(self.client.delete(f"/access-groups/{group_id}").status_code, 204)
        self.assertEqual(self.client.delete(f"/access-groups/{group_id}").status_code, 404)
