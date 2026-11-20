import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from agenti.agency import office
from agenti.agency.tools import Context
from agenti.agency.tools_catalog import agent_forge, automations
from agenti.people import people, private_store


class TestAgencyAgentAutonomy(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.people_dir = Path(self.tmp.name) / "people"
        self.people_dir.mkdir(parents=True, exist_ok=True)
        self.patchers = [
            mock.patch.object(people, "PEOPLE_DIR", self.people_dir),
            mock.patch.object(private_store, "KEY_FILE", self.people_dir / "people.key"),
        ]
        for p in self.patchers:
            p.start()
        self.created_tools = []

    def tearDown(self):
        for t in self.created_tools:
            Path(t).unlink(missing_ok=True)
        for p in self.patchers:
            p.stop()
        self.tmp.cleanup()

    async def test_agent_creates_domain_automation_autonomously(self):
        ctx = Context(project_id="p1", folder=".", worker="culinary_chef")
        raw = await agent_forge._agent_create_automation(ctx, {
            "trigger_event": "quando l'acqua della pasta bolle",
            "action_payload": "invia avviso sonoro e avvia timer cottura 11 minuti",
            "description": "Automazione autonoma dello chef per la cottura pasta",
        })
        res = json.loads(raw)
        self.assertEqual(res["status"], "automation_created_by_agent")
        self.assertEqual(res["creator_agent"], "culinary_chef")

        active = automations.get_active_automations()
        self.assertTrue(any("bolle" in a["trigger"] for a in active))

    async def test_agent_forges_tool_autonomously(self):
        ctx = Context(project_id="p1", folder=".", worker="field_tech")
        test_tool_name = "test_opt_sensor_ping"
        expected_path = agent_forge.TOOLS_CATALOG_DIR / f"{test_tool_name}.py"
        self.created_tools.append(expected_path)

        raw = await agent_forge._agent_forge_tool(ctx, {
            "tool_name": test_tool_name,
            "description": "Strumento forgiato dal tecnico per il ping rapido",
            "args": {"target_ip": "string"},
        })
        res = json.loads(raw)
        self.assertEqual(res["status"], "tool_forged_by_agent")
        self.assertEqual(res["creator_agent"], "field_tech")
        self.assertTrue(expected_path.exists())

    async def test_agent_forges_borderless_glassmorphic_widget(self):
        ctx = Context(project_id="p1", folder=".", worker="education_tutor")
        widget_id = "widget_socratic_step_meter"
        raw = await agent_forge._agent_forge_widget(ctx, {
            "agent_id": "education_tutor",
            "widget_id": widget_id,
            "title": "Misuratore Autonomia Socratico",
            "widget_type": "socratic_gauge",
            "glow_color": "cyan",
            "data_bindings": {"metric": "autonomy_index"},
        })
        res = json.loads(raw)
        self.assertEqual(res["status"], "widget_forged_and_mounted")
        self.assertEqual(res["widget"]["style"], "borderless_glassmorphic")
        self.assertEqual(res["widget"]["visual"]["border"], "none")
        self.assertEqual(res["widget"]["visual"]["background"], "transparent")

        dyn_widgets = office.get_agent_dynamic_widgets("education_tutor")
        self.assertTrue(any(w["id"] == widget_id for w in dyn_widgets))

        base = {"tasks": [], "roles": ["education_tutor"], "tools": [], "questions": []}
        focus = office.enrich_focus({}, base)
        agent_cards = focus["office"]["agents"]
        edu_agent = next((a for a in agent_cards if a.get("id") == "education_tutor"), None)
        if edu_agent:
            self.assertTrue(any(w["id"] == widget_id for w in edu_agent.get("widgets", [])))


if __name__ == "__main__":
    unittest.main()
