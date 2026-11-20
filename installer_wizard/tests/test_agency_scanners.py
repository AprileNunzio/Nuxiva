import json
import tempfile
import unittest
from pathlib import Path

from agenti.agency.office import _build_agents_and_desks, enrich_focus
from agenti.agency.scanner.department_scanner import (
    find_specialist,
    forge_department,
    scan_departments,
)
from agenti.agency.scanner.tool_scanner import scan_tools
from agenti.agency.tools import Context, call
from agenti.agency.tools_catalog.automations import get_active_automations


class TestAgencyScanners(unittest.IsolatedAsyncioTestCase):
    def test_department_scanner_loads_from_directory(self):
        deps = scan_departments()
        self.assertIn("architect", deps)
        self.assertIn("medical", deps)
        self.assertIn("legal", deps)
        self.assertIn("customer", deps)
        self.assertIn("finance", deps)
        self.assertIn("sales", deps)
        self.assertIn("integrations", deps)
        for dep in deps.values():
            self.assertTrue(len(dep["skills"]) > 0)
            self.assertTrue(len(dep["widgets"]) > 0)
            self.assertTrue(Path(dep["path"]).exists())

    def test_tool_scanner_loads_from_directory(self):
        tools = scan_tools()
        self.assertIn("read_invoice", tools)
        self.assertIn("create_invoice", tools)
        self.assertIn("whatsapp_send", tools)
        self.assertIn("twilio_voice_dispatch", tools)
        self.assertIn("email_dispatch", tools)
        self.assertIn("mcp_gateway", tools)
        self.assertIn("create_automation", tools)
        self.assertIn("list_automations", tools)
        self.assertIn("forge_department_agent", tools)
        self.assertIn("list_departments", tools)
        self.assertIn("ask_clarification", tools)

    def test_find_and_forge_department_on_demand(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            temp_path = Path(tmp_dir)
            spec = find_specialist("medicina clinica farmaci", [temp_path])
            self.assertIsNotNone(spec)
            self.assertEqual(spec["id"], "medical")

            missing_spec = find_specialist("astrofisica galassie quantistica", [temp_path])
            self.assertIsNone(missing_spec)

            forged = forge_department(
                domain="astrophysics",
                name="Prof. Galileo · Astrophysics Specialist",
                dept_name="Dipartimento Astrofisica & Spazio",
                prompt="Esperto in calcoli orbitali e astrofisica computazionale.",
                skills=["orbital-mechanics", "cosmology", "tensor-math"],
                widgets=[{"id": "orbit_tracker", "type": "telescope_view", "title": "Tracciamento Orbite"}],
                target_dir=temp_path,
            )
            self.assertEqual(forged["id"], "astrophysics")
            scanned = scan_departments([temp_path])
            self.assertIn("astrophysics", scanned)
            found_now = find_specialist("astrofisica galassie", [temp_path])
            self.assertIsNotNone(found_now)
            self.assertEqual(found_now["id"], "astrophysics")

    async def test_event_driven_automation_flow(self):
        ctx = Context(project_id="test_p", folder="/tmp/test_proj")
        res_str = await call(ctx, "create_automation", {
            "name": "Chiamami quando arriva email di Angelika",
            "trigger": {"type": "email_received", "from": "angelika@domain.com"},
            "action": {
                "type": "twilio_call",
                "phone_number": "+393339998888",
                "speech_script": "Signore, è appena arrivata una nuova email da Angelika.",
            },
            "description": "Chiama automaticamente l'utente sul telefono all'arrivo dell'email di Angelika.",
            "widget": {"id": "angelika_watcher", "type": "event_card", "title": "Monitor Email Angelika"},
        })
        res = json.loads(res_str)
        self.assertEqual(res["status"], "created")
        self.assertEqual(res["trigger"]["from"], "angelika@domain.com")
        self.assertEqual(res["action"]["type"], "twilio_call")

        active = get_active_automations()
        matched = [a for a in active if a["name"] == "Chiamami quando arriva email di Angelika"]
        self.assertTrue(len(matched) > 0)
        self.assertTrue(matched[0]["active"])

    async def test_ask_clarification_loop(self):
        ctx = Context(project_id="test_p", folder="/tmp/test_proj")
        res_str = await call(ctx, "ask_clarification", {
            "question": "A quale numero telefonico desideri ricevere la chiamata di allerta per l'email di Angelika?",
            "options": ["+393331234567", "+39021234567", "Altro numero personalizzato"],
        })
        res = json.loads(res_str)
        self.assertEqual(res["status"], "awaiting_user_input")
        self.assertEqual(res["dialogue_turn"], "clarification_prompt")
        self.assertIn("numero telefonico", res["question"])
        self.assertEqual(len(res["options"]), 3)

    async def test_forge_department_agent_tool(self):
        ctx = Context(project_id="test_p", folder="/tmp/test_proj")
        created_file = Path(__file__).resolve().parents[1] / "agenti" / "cognizione" / "agency" / "departments_catalog" / "veterinary.json"
        try:
            res_str = await call(ctx, "forge_department_agent", {
                "domain": "veterinary",
                "agent_name": "Dr. Ugo · Senior Veterinary Surgeon",
                "department_name": "Dipartimento Veterinario & Salute Animale",
                "system_prompt": "Diagnosi e protocolli terapeutici veterinari evidence-based.",
                "skills": ["animal-triage", "zoology", "surgery-protocols"],
            })
            res = json.loads(res_str)
            self.assertEqual(res["status"], "forged")
            self.assertEqual(res["department_id"], "veterinary")
            self.assertEqual(res["department"], "Dipartimento Veterinario & Salute Animale")
        finally:
            if created_file.exists():
                created_file.unlink()

    def test_dynamic_desks_allocation_beyond_twelve(self):
        roles = [{"id": f"role_{i}", "mission": f"Mission {i}"} for i in range(16)]
        tasks = [{"id": f"t_{i}", "role": f"role_{i}", "status": "pending", "title": f"Task {i}"} for i in range(16)]
        agents, desks = _build_agents_and_desks(roles, tasks, [], "running")
        self.assertTrue(len(desks) >= 16)
        self.assertTrue(len(agents) >= 16)
        extra_desk = desks[14]
        self.assertEqual(extra_desk["zone"], "Reparti Specializzati Dinamici")
        self.assertGreater(extra_desk["z"], 4.0)

    def test_enrich_focus_includes_automations_and_widgets(self):
        base = {
            "id": "p_enterprise",
            "goal": "Gestire azienda omnicanale",
            "status": "running",
            "roles": [{"id": "medical", "mission": "Consulenza medica"}],
            "tasks": [{"id": "t1", "role": "medical", "title": "Analisi farmaci", "status": "running"}],
            "tools": ["read_invoice", "create_automation"],
        }
        res = enrich_focus({"project": {"title": "Azienda Demo"}}, base)
        office = res["office"]
        self.assertIn("active_automations", office)
        self.assertIn("department_widgets", office)
        self.assertTrue(any("clinical" in str(w).lower() or "medical" in str(w).lower() for w in office["department_widgets"]))
