import unittest
import json
from unittest.mock import AsyncMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
import httpx

from features.repair_workbench import api
from features.repair_workbench import commands
from feature_api_scanner import discover_feature_apis, discover_feature_connectors


class WorkbenchProxyTest(unittest.TestCase):
    def test_manifest_discovers_api_in_both_surfaces(self):
        self.assertIn(api, discover_feature_apis())
        self.assertIs(api.admin_routes, api.public_routes)
        self.assertEqual(discover_feature_connectors()["repair_workbench"], "features.repair_workbench.commands")

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

    def test_standalone_page_uses_built_client(self):
        response = self.client.get("/repair-workbench")
        self.assertEqual(response.status_code, 200)
        self.assertIn('id="root"', response.text)

    def test_internal_vision_rejects_remote_unsigned_call(self):
        self.assertEqual(self.client.post("/api/internal/repair-workbench/analyze", json={}).status_code, 403)


class WorkbenchCommandTest(unittest.IsolatedAsyncioTestCase):
    async def test_vision_falls_back_when_structured_output_is_invalid(self):
        from features.brain import sight
        from server.features.repair_workbench.session_models import VisionObservation
        with patch.object(sight, "models", new=AsyncMock(return_value=["first", "second"])), \
             patch.object(sight, "_ollama", new=AsyncMock(side_effect=[
                 '{"components":[{"label":"R1","bbox":[2,0,3,1]}]}',
                 json.dumps({"summary": "Scheda osservata", "components": []}),
             ])) as inference:
            result, model = await sight.look(b"frame", "Inspect", as_json=True, validator=VisionObservation.model_validate)
        self.assertEqual(model, "second")
        self.assertEqual(result["summary"], "Scheda osservata")
        self.assertEqual(inference.await_count, 2)

    async def test_public_command_creates_session_and_opens_dedicated_widget(self):
        responses = [httpx.Response(200, json={"project": {"project_id": "project"}}, request=httpx.Request("POST", "http://core/projects")),
                     httpx.Response(200, json={"session": {"session_id": "session"}}, request=httpx.Request("POST", "http://core/sessions"))]
        with patch.object(commands.live, "listing", return_value=[{"id": "camera", "name": "Telecamera Banco Riparazioni"}]), \
             patch.object(commands.core, "request", new=AsyncMock(side_effect=responses)) as request, \
             patch.object(commands.desk, "scan"), patch.object(commands.desk, "show") as show, \
             patch.object(commands.desk, "fullscreen") as fullscreen:
            speech, _ = await commands.answer("Apri un nuovo progetto per aggiustare una scheda elettronica")
        self.assertIn("Telecamera Banco Riparazioni", speech)
        self.assertEqual(request.await_count, 2)
        self.assertEqual(show.call_args.args[0], "repair_workbench")
        self.assertEqual(show.call_args.args[1]["session_id"], "session")
        fullscreen.assert_called_once_with("repair:project", True)

    async def test_missing_camera_does_not_claim_to_have_started(self):
        with patch.object(commands.live, "listing", return_value=[]), \
             patch.object(commands.core, "request", new=AsyncMock()) as request:
            speech, _ = await commands.answer("Apri un nuovo progetto per aggiustare una scheda elettronica")
        self.assertIn("Non trovo", speech)
        request.assert_not_awaited()

    async def test_other_requests_keep_existing_routing(self):
        with patch.object(commands.desk, "instances", {}), self.assertRaises(LookupError):
            await commands.answer("Che tempo fa?")


if __name__ == "__main__":
    unittest.main()
