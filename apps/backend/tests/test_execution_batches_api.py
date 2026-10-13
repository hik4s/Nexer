import tempfile
import unittest
from pathlib import Path
from sqlalchemy import create_engine, select, func
from sqlalchemy.orm import sessionmaker
from app.models import Base, Automation, AutomationVersion, Execution
from app.database import get_db
from app.main import app
from test_client import AuthenticatedTestClient

class ExecutionBatchTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.engine = create_engine("sqlite:///" + str(Path(self.tmp.name) / "batches.db"), connect_args={"check_same_thread": False})
        Base.metadata.create_all(self.engine); self.factory = sessionmaker(bind=self.engine)
        def override():
            with self.factory() as db: yield db
        app.dependency_overrides[get_db] = override; self.client = AuthenticatedTestClient(app)
        self.ids = []
        with self.factory() as db:
            for index in range(2):
                automation = Automation(code=f"FLOW{index}", name=f"Flow {index}", status="PUBLISHED", current_version=1)
                db.add(automation); db.flush(); self.ids.append(automation.id)
                recipe = {"schema_version": 1, "name": "Flow", "variables": {"company": {"type": "string", "required": True}}, "steps": [{"id": "fill", "action": "fill", "selector": "input", "value": "{{company}}"}], "output": {"type": "file"}}
                db.add(AutomationVersion(automation_id=automation.id, version=1, recipe=recipe, test_status="PASSED"))
            db.commit()
    def tearDown(self):
        self.client.close(); app.dependency_overrides.clear(); self.engine.dispose(); self.tmp.cleanup()
    def payload(self):
        return {"name": "My batch", "idempotency_key": "synthetic-batch-key-001", "items": [{"automation_id": aid, "version": 1, "inputs": {"company": f"company-{index}"}, "test_mode": True} for index, aid in enumerate(self.ids)]}
    def test_batch_is_idempotent_has_separate_inputs_and_cancels_individually(self):
        body = self.payload(); response = self.client.post("/execution-batches", json=body)
        self.assertEqual(response.status_code, 201)
        batch = response.json()
        self.assertEqual(len(batch["executions"]), 2)
        self.assertNotEqual(batch["executions"][0]["id"], batch["executions"][1]["id"])
        self.assertEqual(batch["executions"][0]["inputs"], {"company": "company-0"})
        self.assertEqual(batch["executions"][1]["inputs"], {"company": "company-1"})
        replay = self.client.post("/execution-batches", json=body)
        self.assertEqual(replay.json()["id"], batch["id"])
        with self.factory() as db: self.assertEqual(db.scalar(select(func.count()).select_from(Execution)), 2)
        first = batch["executions"][0]["id"]
        self.assertEqual(self.client.post(f"/executions/{first}/cancel").status_code, 200)
        partial = self.client.get(f"/execution-batches/{batch['id']}").json()
        self.assertEqual(partial["executions"][1]["status"], "QUEUED")
        stopped = self.client.post(f"/execution-batches/{batch['id']}/cancel")
        self.assertEqual(stopped.status_code, 200); self.assertEqual(stopped.json()["status"], "CANCELLED")
    def test_invalid_item_rolls_back_entire_batch_and_reused_key_rejects_new_payload(self):
        body = self.payload(); body["items"][1]["automation_id"] = 99999
        self.assertEqual(self.client.post("/execution-batches", json=body).status_code, 404)
        with self.factory() as db: self.assertEqual(db.scalar(select(func.count()).select_from(Execution)), 0)
        body = self.payload(); self.assertEqual(self.client.post("/execution-batches", json=body).status_code, 201)
        body["items"][0]["inputs"]["company"] = "changed"
        self.assertEqual(self.client.post("/execution-batches", json=body).status_code, 409)
    def test_missing_required_input_prevents_enqueue(self):
        body = self.payload(); body["items"][1]["inputs"] = {}
        self.assertEqual(self.client.post("/execution-batches", json=body).status_code, 422)
        with self.factory() as db: self.assertEqual(db.scalar(select(func.count()).select_from(Execution)), 0)
