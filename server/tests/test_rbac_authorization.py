import unittest
import tempfile
from pathlib import Path
from unittest import mock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from server.core.security_guard import rbac_controller as controller
from server.core.security_guard.rbac_service import RBACService


class RBACAuthorizationTests(unittest.TestCase):
    def setUp(self):
        app = FastAPI()
        app.include_router(controller.rbac_router, prefix="/api/v1")
        self.client = TestClient(app)

    def test_every_management_route_requires_credentials(self):
        for method, path in [("GET", "/users"), ("GET", "/roles"), ("POST", "/users"), ("DELETE", "/users/other")]:
            self.assertEqual(self.client.request(method, "/api/v1/rbac" + path).status_code, 401)

    def test_device_token_cannot_impersonate_owner_using_subject(self):
        with mock.patch.object(controller.token_provider, "verify_token", return_value={"sub": "user_primary", "claims": {"role": "OPERATOR"}}), mock.patch.object(controller.rbac_service, "has_permission") as permission:
            response = self.client.get("/api/v1/rbac/roles", headers={"Authorization": "Bearer valid-device-token"})
        self.assertEqual(response.status_code, 403)
        permission.assert_not_called()

    def test_verified_actor_still_needs_management_permission(self):
        with mock.patch.object(controller.token_provider, "verify_token", return_value={"claims": {"user_id": "auditor"}}), mock.patch.object(controller.rbac_service, "has_permission", return_value=False):
            response = self.client.get("/api/v1/rbac/roles", headers={"Authorization": "Bearer verified"})
        self.assertEqual(response.status_code, 403)

    def test_authorized_actor_can_read_role_matrix(self):
        with mock.patch.object(controller.token_provider, "verify_token", return_value={"claims": {"user_id": "owner"}}), mock.patch.object(controller.rbac_service, "has_permission", return_value=True) as permission:
            response = self.client.get("/api/v1/rbac/roles", headers={"Authorization": "Bearer verified"})
        self.assertEqual(response.status_code, 200)
        permission.assert_called_once_with("owner", controller.ResourcePermission.RBAC_MANAGE)


class RBACStorageTests(unittest.TestCase):
    def test_corrupt_store_is_preserved_without_recreating_an_owner(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "users.json"
            path.write_text("broken policy", encoding="utf-8")
            service = object.__new__(RBACService)
            service._users_file = str(path)
            service._users = {}
            service._load_users()
            self.assertEqual(service.list_users(), [])
            self.assertFalse(service.has_permission("user_primary", controller.ResourcePermission.RBAC_MANAGE))
            self.assertEqual(path.read_text(encoding="utf-8"), "broken policy")

    def test_failed_persistence_does_not_grant_in_memory_permissions(self):
        service = object.__new__(RBACService)
        service._users = {}
        service._load_error = False
        user = controller.UserAccount(user_id="new", username="new", display_name="New", profile="home", role="owner_admin")
        with mock.patch.object(service, "_save_users", side_effect=OSError("disk full")):
            with self.assertRaises(OSError):
                service.upsert_user(user)
        self.assertIsNone(service.get_user("new"))
