import tempfile
import unittest
from pathlib import Path
from unittest import mock

from fastapi.testclient import TestClient

import nuxiva_supervisor
from features.agent import registry
from features.team import control as control_module
from features.team import priority

HEADERS = {"X-Nuxiva-Request": "1"}


class TeamControlStoreTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = control_module.TeamControl(Path(self.tmp.name) / "team.json")

    def tearDown(self):
        self.tmp.cleanup()

    def test_agent_priority_and_instructions_persist(self):
        self.store.set_agent("music", {"priority": 120, "instructions": "Volume basso dopo le 22 <script>"})
        fresh = control_module.TeamControl(self.store.path)
        self.assertEqual(fresh.priority("music"), 120)
        self.assertNotIn("<", fresh.instructions("music"))
        self.assertEqual(self.store.path.stat().st_mode & 0o777, 0o600)

    def test_invalid_values_rejected(self):
        for changes in ({"priority": 999}, {"priority": True}, {"priority": "10"}):
            with self.assertRaises(ValueError):
                self.store.set_agent("music", changes)
        with self.assertRaises(ValueError):
            self.store.set_agent("../x", {"priority": 1})
        with self.assertRaises(ValueError):
            self.store.set_tool("play", {"agent": "ghost"}, {"music"})
        with self.assertRaises(ValueError):
            self.store.set_widget("clock", {"people": ["eve"]}, {"desktop"}, {"nunzio"})

    def test_tool_and_widget_overrides(self):
        self.store.set_tool("play", {"agent": "music", "enabled": False, "always_confirm": True}, {"music"})
        self.assertEqual(self.store.tool_owner("play"), "music")
        self.assertFalse(self.store.tool_enabled("play"))
        self.assertTrue(self.store.tool_forced_confirm("play"))
        self.store.set_tool("play", {"agent": "", "enabled": True, "always_confirm": False}, {"music"})
        self.assertEqual(self.store.tool("play"), {})
        self.store.set_widget("clock", {"agent": "desktop", "people": ["nunzio"]}, {"desktop"}, {"nunzio"})
        self.assertEqual(self.store.widget_people("clock"), ["nunzio"])
        self.store.forget_agent("desktop")
        self.assertIsNone(self.store.widget_owner("clock"))


class TeamControlEnforcementTest(unittest.IsolatedAsyncioTestCase):
    async def test_disabled_tool_is_hidden_and_refused(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        store = control_module.TeamControl(Path(tmp.name) / "team.json")

        async def probe() -> str:
            return "ok"

        registry.TOOLS["probe_tool_x"] = {"name": "probe_tool_x", "description": "", "args": {}, "fn": probe, "confirm": False,
                                          "full_only": False, "agent": "agent", "verify": None, "precheck": None}
        self.addCleanup(registry.TOOLS.pop, "probe_tool_x", None)
        with mock.patch.object(control_module, "control", store):
            self.assertEqual(await registry.run("probe_tool_x", {}), "ok")
            store.set_tool("probe_tool_x", {"enabled": False, "always_confirm": True, "agent": "music"}, {"music"})
            self.assertNotIn("probe_tool_x", [t["name"] for t in registry.available("completo")])
            self.assertTrue(registry.needs_confirm("probe_tool_x", {}))
            with self.assertRaises(registry.ToolDisabled):
                await registry.run("probe_tool_x", {})
            store.set_agent("music", {"priority": 7})
            self.assertEqual(priority.of("music"), 7)


class TeamApiTest(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(nuxiva_supervisor.admin)
        self.client.post("/api/auth/login", json={"username": "admin", "password": "nuxiva"}, headers=HEADERS)

    def test_requires_login_and_csrf(self):
        self.assertEqual(TestClient(nuxiva_supervisor.admin).get("/api/team").status_code, 401)
        self.assertEqual(self.client.put("/api/team/music", json={"priority": 10}).status_code, 403)

    def test_overview_and_validation(self):
        data = self.client.get("/api/team").json()
        self.assertTrue(data["agents"])
        self.assertIn("tools", data)
        self.assertIn("widgets", data)
        self.assertEqual(self.client.put("/api/team/ghost-agent", json={"priority": 10}, headers=HEADERS).status_code, 404)
        self.assertEqual(self.client.put("/api/team/tools/team_roster", json={"enabled": False}, headers=HEADERS).status_code, 409)
        self.assertEqual(self.client.post("/api/team/music/message", json={"text": ""}, headers=HEADERS).status_code, 400)
        self.assertEqual(self.client.delete("/api/team/agents/music", headers=HEADERS).status_code, 409)


if __name__ == "__main__":
    unittest.main()
