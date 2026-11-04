import tempfile
import unittest
import unittest.mock
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from access import require_admin
from features.fleet import api, catalog, tools
from features.fleet.service import FleetService

HEADERS = {"X-Nuxiva-Request": "1"}


class FleetApiTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.service = FleetService(Path(self.tmp.name))
        patches = [
            unittest.mock.patch.object(api, "fleet", self.service),
            unittest.mock.patch.object(tools, "fleet", self.service),
            unittest.mock.patch.object(catalog, "_registry", lambda: {"play_music": {"description": "riproduce musica"}}),
            unittest.mock.patch.object(catalog, "_widgets", lambda: {"clock": {"name": "Orologio", "description": "ora"}}),
        ]
        for patch in patches:
            patch.start()
            self.addCleanup(patch.stop)
        self.app = FastAPI()
        self.app.include_router(api.admin_routes)
        self.client = TestClient(self.app)

    def test_every_route_requires_a_session(self):
        for method, path in (("get", "/api/fleet/summary"), ("get", "/api/fleet/agents"), ("post", "/api/fleet/agents"),
                             ("delete", "/api/fleet/agents/musica"), ("post", "/api/fleet/bulk/state")):
            self.assertEqual(getattr(self.client, method)(path, headers=HEADERS).status_code, 401, path)

    def test_crud_links_and_errors_are_coded(self):
        self.app.dependency_overrides[require_admin] = lambda: "nunzio"
        created = self.client.post("/api/fleet/agents", json={"name": "Musica", "tools": ["play_music"]}, headers=HEADERS)
        self.assertEqual((created.status_code, created.json()["id"]), (200, "musica"))
        self.assertEqual(self.client.post("/api/fleet/agents", json={"name": "Musica"}, headers=HEADERS).json()["detail"], "exists")
        self.assertEqual(self.client.post("/api/fleet/agents", json={"name": "Zeta", "tools": ["nope"]}, headers=HEADERS).status_code, 422)
        listing = self.client.get("/api/fleet/agents?limit=5&state=active").json()
        self.assertEqual([item["id"] for item in listing["items"]], ["musica"])
        self.assertEqual(self.client.get("/api/fleet/agents?state=zombie").json()["detail"], "invalid_filter")
        self.assertEqual(self.client.get("/api/fleet/agents?cursor=%%%").status_code, 400)
        attached = self.client.post("/api/fleet/agents/musica/links", json={"kind": "widget", "refs": ["clock"]}, headers=HEADERS)
        self.assertEqual(attached.json()["widgets"], ["clock"])
        detached = self.client.delete("/api/fleet/agents/musica/links/widget/clock", headers=HEADERS)
        self.assertEqual(detached.json()["widgets"], [])
        self.assertEqual(self.client.put("/api/fleet/agents/musica", json={"state": "paused"}, headers=HEADERS).json()["state"], "paused")
        self.assertEqual(self.client.post("/api/fleet/bulk/state", json={"state": "archived"}, headers=HEADERS).json()["changed"], 1)
        self.assertEqual(self.client.get("/api/fleet/summary").json()["state"]["archived"], 1)
        self.assertEqual(self.client.get("/api/fleet/catalog?kind=tool&q=play").json()["items"][0]["id"], "play_music")
        self.assertEqual(self.client.delete("/api/fleet/agents/musica", headers=HEADERS).status_code, 200)
        self.assertEqual(self.client.get("/api/fleet/agents/musica").status_code, 404)


class FleetToolsTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.service = FleetService(Path(self.tmp.name))
        for patch in (unittest.mock.patch.object(tools, "fleet", self.service),
                      unittest.mock.patch.object(catalog, "_registry", lambda: {"play_music": {"description": "riproduce musica in casa"}}),
                      unittest.mock.patch.object(catalog, "_widgets", lambda: {})):
            patch.start()
            self.addCleanup(patch.stop)

    async def test_nuxiva_creates_once_and_picks_tools(self):
        first = await tools.fleet_create("Dj di casa", "riprodurre musica in casa")
        self.assertIn("play_music", first)
        self.assertIn("dj-di-casa", first)
        again = await tools.fleet_create("Dj di casa", "riprodurre musica in casa")
        self.assertIn("esiste già", again)
        self.assertEqual(self.service.store.summary()["total"], 1)
        self.assertIn("dj-di-casa", await tools.fleet_find("dj"))
        await tools.fleet_retire("dj-di-casa")
        self.assertEqual(self.service.store.get("dj-di-casa")["state"], "archived")

    async def test_failures_surface_as_errors(self):
        with self.assertRaises(ValueError):
            await tools.fleet_attach("missing-one", "tool", "play_music")


if __name__ == "__main__":
    unittest.main()
