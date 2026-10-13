import test_execution_batches_api as batch_fixture
from app.models import Base

class PracticalWorkspaceTests(batch_fixture.ExecutionBatchTests):
    test_batch_is_idempotent_has_separate_inputs_and_cancels_individually = None
    test_invalid_item_rolls_back_entire_batch_and_reused_key_rejects_new_payload = None
    test_missing_required_input_prevents_enqueue = None
    def test_flow_finish_errors_distinguish_preparation_from_browser_failure(self):
        from unittest.mock import patch
        from app.services.flow_recordings import flow_recordings
        cases = (("FLOW_RECORDING_PREPARING", "Conclua o login no Edge"), ("broken-pipe-private-canary", "Verifique a janela do Edge"))
        for error, guidance in cases:
            with self.subTest(error=error), patch.object(flow_recordings, "get", return_value={"id": "fixture", "status": "RECORDING"}), patch.object(flow_recordings, "finish", side_effect=RuntimeError(error)):
                response = self.client.post("/flow-recordings/fixture/finish")
                self.assertEqual(response.status_code, 409)
                self.assertIn(guidance, response.text)
                self.assertNotIn("broken-pipe-private-canary", response.text)

    def test_group_associates_profiles_without_storing_credentials(self):
        response = self.client.post("/access-groups", json={"name": "Energisa"})
        self.assertEqual(response.status_code, 201)
        group = response.json()
        profile = self.client.post("/login-profiles", json={"name": "Destino A", "login_url": "https://site.invalid/login", "group_id": group["id"]})
        self.assertEqual(profile.status_code, 201)
        self.assertEqual(profile.json()["group_id"], group["id"])
        self.assertEqual(self.client.post("/access-groups", json={"name": "Oops", "password": "secret-canary"}).status_code, 422)
        self.assertNotIn("secret-canary", self.client.get("/access-groups").text)
    def test_favorite_saves_only_declared_nonsecret_parameters(self):
        response = self.client.post("/routines", json={"name": "Mensal", "items": [{"automation_id": self.ids[0], "version": 1, "inputs": {"company": "A"}}, {"automation_id": self.ids[1], "version": 1, "inputs": {}}]})
        self.assertEqual(response.status_code, 201)
        routine = response.json()
        self.assertEqual(self.client.get(f"/routines/{routine['id']}").json()["items"][0]["inputs"], {"company": "A"})
        rejected = self.client.post("/routines", json={"name": "Invalid", "items": [{"automation_id": self.ids[0], "version": 1, "inputs": {"password": "secret-canary"}}]})
        self.assertEqual(rejected.status_code, 422)
        self.assertNotIn("secret-canary", self.client.get("/routines").text)
        self.assertEqual(self.client.delete(f"/routines/{routine['id']}").status_code, 204)
        self.assertEqual(self.client.get(f"/routines/{routine['id']}").status_code, 404)
    def test_guided_publish_and_favorite_do_not_execute_until_explicit_start(self):
        from sqlalchemy import select, func
        from app.models import Execution
        created = self.client.post("/automations", json={"code": "GUIDED_LOCAL", "name": "Guided local"})
        self.assertEqual(created.status_code, 201)
        identity = created.json()["id"]
        recipe = {"schema_version": 1, "name": "Guided local", "site_url": "http://127.0.0.1:8765/form", "variables": {"base_url": {"type": "string", "required": True}, "company": {"type": "string", "label": "Empresa"}}, "steps": [{"id": "open", "action": "navigate", "url": "{{base_url}}"}, {"id": "fill", "action": "fill", "selector": "#company", "value": "{{company}}"}], "output": {"type": "file"}}
        version = self.client.post(f"/automations/{identity}/versions", json={"recipe": recipe, "created_by": "guided"})
        self.assertEqual(version.status_code, 201)
        number = version.json()["version"]
        self.assertEqual(self.client.post(f"/automations/{identity}/versions/{number}/test").status_code, 200)
        self.assertEqual(self.client.post(f"/automations/{identity}/versions/{number}/publish").status_code, 200)
        self.assertEqual(self.client.post("/routines", json={"name": "Favorite", "items": [{"automation_id": identity, "version": number, "inputs": {}}]}).status_code, 201)
        with self.factory() as db: self.assertEqual(db.scalar(select(func.count()).select_from(Execution)), 0)
        started = self.client.post("/execution-batches", json={"name": "Explicit start", "idempotency_key": "guided-start-key-001", "items": [{"automation_id": identity, "version": number, "inputs": {"base_url": "http://127.0.0.1:8765/form", "company": "New execution company"}, "test_mode": True}]})
        self.assertEqual(started.status_code, 201)
