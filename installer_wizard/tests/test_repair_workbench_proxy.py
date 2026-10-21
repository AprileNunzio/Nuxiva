import unittest
from unittest.mock import AsyncMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
import httpx

from features.repair_workbench import api
from feature_api_scanner import discover_feature_apis


class WorkbenchProxyTest(unittest.TestCase):
    def test_manifest_discovers_api_in_both_surfaces(self):
        self.assertIn(api, discover_feature_apis())
        self.assertIs(api.admin_routes, api.public_routes)

    def setUp(self):
        app = FastAPI()
        app.include_router(api.public_routes)
        self.client = TestClient(app)
        self.addCleanup(self.client.close)
        self.access = patch.object(api, "require_display")
        self.access.start()
        self.addCleanup(self.access.stop)
        self.core = patch.object(api.core, "request", new=AsyncMock(return_value=httpx.Response(200, json={"status": "success"})))
        self.request = self.core.start()
        self.addCleanup(self.core.stop)

    def test_get_projects_maps_only_to_core_projects(self):
        response = self.client.get("/api/v1/repair-workbench/projects?user_id=another")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.request.call_args.args, ("GET", "/api/v1/projects"))
        self.assertEqual(self.request.call_args.kwargs["params"], {"user_id": "user_primary"})

    def test_mutations_require_request_header(self):
        response = self.client.post("/api/v1/repair-workbench/sessions", json={})
        self.assertEqual(response.status_code, 403)
        self.request.assert_not_awaited()

    def test_analysis_body_and_status_are_preserved(self):
        self.request.return_value = httpx.Response(503, json={"code": "VISION_UNAVAILABLE"})
        response = self.client.post("/api/v1/repair-workbench/sessions/session/analyze-frame",
                                    json={"frame_base64": "frame"}, headers={"X-Nuxiva-Request": "1"})
        self.assertEqual(response.status_code, 503)
        self.assertEqual(self.request.call_args.kwargs["json"], {"frame_base64": "frame"})

    def test_unlisted_routes_are_not_forwarded(self):
        self.assertEqual(self.client.get("/api/v1/repair-workbench/admin").status_code, 404)
        self.request.assert_not_awaited()

    def test_core_unavailable_is_explicit(self):
        self.request.side_effect = httpx.ConnectError("offline")
        self.assertEqual(self.client.get("/api/v1/repair-workbench/launch-requests").status_code, 502)


if __name__ == "__main__":
    unittest.main()
