import unittest
import test_login_profiles_api as fixtures
from app.models import AccessGroup, Automation, AutomationVersion, Execution, LoginProfile, LoginProfileVersion
from sqlalchemy import select


class LoginProfileDeletionTests(unittest.TestCase):
    setUp = fixtures.LoginProfileApiTests.setUp
    tearDown = fixtures.LoginProfileApiTests.tearDown
    def create_profile(self):
        return self.client.post("/login-profiles", json={"name": "Site", "login_url": "https://site.invalid/login"}).json()

    def test_permanent_delete_removes_all_versions_and_preserves_group_and_execution_snapshot(self):
        profile = self.create_profile()
        pid = profile["id"]
        self.client.post(f"/login-profiles/{pid}/versions", json=profile["configuration"])
        snapshot = {str(pid): {"configuration": profile["configuration"], "version": 1}}
        with self.factory() as db:
            group = AccessGroup(name="Grupo preservado")
            db.add(group); db.flush()
            db.get(LoginProfile, pid).group_id = group.id
            history = Execution(name="Histórico", status="COMPLETED", login_profiles=snapshot)
            db.add(history); db.commit()
            group_id, execution_id = group.id, history.id
        response = self.client.delete(f"/login-profiles/{pid}/permanent")
        self.assertEqual(response.status_code, 204)
        self.assertEqual(response.content, b"")
        self.assertEqual(self.client.get(f"/login-profiles/{pid}").status_code, 404)
        self.assertEqual(self.client.get("/login-profiles").json()["total"], 0)
        with self.factory() as db:
            self.assertEqual(db.scalars(select(LoginProfileVersion).where(LoginProfileVersion.profile_id == pid)).all(), [])
            self.assertIsNotNone(db.get(AccessGroup, group_id))
            self.assertEqual(db.get(Execution, execution_id).login_profiles, snapshot)

    def test_any_saved_recipe_version_blocks_delete_and_preserves_profile(self):
        profile = self.create_profile()
        pid = profile["id"]
        with self.factory() as db:
            automation = Automation(code="LINKED", name="Automação", current_version=2)
            db.add(automation); db.flush()
            db.add_all([AutomationVersion(automation_id=automation.id, version=1, recipe={"login_profile": {"id": pid, "version": 1}}), AutomationVersion(automation_id=automation.id, version=2, recipe={})])
            db.commit()
        response = self.client.delete(f"/login-profiles/{pid}/permanent")
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["error"]["code"], "LOGIN_PROFILE_IN_USE")
        self.assertIn("Desative", response.json()["error"]["message"])
        self.assertEqual(self.client.get(f"/login-profiles/{pid}/versions/1").status_code, 200)

    def test_disabled_profile_can_be_deleted_and_old_delete_still_disables(self):
        profile = self.create_profile()
        pid = profile["id"]
        response = self.client.delete(f"/login-profiles/{pid}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "DISABLED")
        self.assertEqual(self.client.get(f"/login-profiles/{pid}/versions/1").status_code, 200)
        self.assertEqual(self.client.delete(f"/login-profiles/{pid}/permanent").status_code, 204)

    def test_missing_profile_returns_not_found(self):
        response = self.client.delete("/login-profiles/999999/permanent")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["error"]["code"], "LOGIN_PROFILE_NOT_FOUND")

    def test_active_selection_prevents_permanent_delete(self):
        from unittest.mock import patch
        from app.services.login_recordings import login_recordings
        profile = self.create_profile()
        with patch.object(login_recordings, "has_active_profile", return_value=True) as active:
            response = self.client.delete(f"/login-profiles/{profile['id']}/permanent")
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["error"]["code"], "LOGIN_PROFILE_RECORDING_ACTIVE")
        active.assert_called_once_with(profile["id"])
        self.assertEqual(self.client.get(f"/login-profiles/{profile['id']}").status_code, 200)
