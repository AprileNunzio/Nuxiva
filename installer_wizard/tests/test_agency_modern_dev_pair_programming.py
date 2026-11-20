import json
import unittest

from agenti.agency import project_room
from agenti.agency.project_scaffolder import project_scaffolder
from agenti.agency.scanner import department_scanner
from agenti.agency.tools import Context
from agenti.agency.tools_catalog import project_architect


class TestAgencyModernDevPairProgramming(unittest.IsolatedAsyncioTestCase):
    def test_modern_specialists_catalog_and_synonyms(self):
        deps = department_scanner.scan_departments()
        for role in ("html5_expert", "tsx_expert", "rust_expert", "php_expert", "security_crypto_expert"):
            self.assertIn(role, deps)
            prof = deps[role]
            self.assertTrue(len(prof["skills"]) >= 4)
            self.assertTrue(len(prof["capabilities"]) >= 3)
            self.assertTrue(len(prof["widgets"]) >= 1)

        spec_tsx = department_scanner.find_specialist("voglio sviluppare interfaccia con tsx e react 19")
        self.assertIsNotNone(spec_tsx)
        self.assertEqual(spec_tsx["id"], "tsx_expert")

        spec_rust = department_scanner.find_specialist("creare microservizio ad alte prestazioni con rust e cargo")
        self.assertIsNotNone(spec_rust)
        self.assertEqual(spec_rust["id"], "rust_expert")

        spec_php = department_scanner.find_specialist("costruire api rest modulari con php8 e symfony")
        self.assertIsNotNone(spec_php)
        self.assertEqual(spec_php["id"], "php_expert")

        spec_html5 = department_scanner.find_specialist("costruire web component pwa in html5 canvas")
        self.assertIsNotNone(spec_html5)
        self.assertEqual(spec_html5["id"], "html5_expert")

        spec_sec = department_scanner.find_specialist("verificare sicurezza crittografia chacha20 e zero trust")
        self.assertIsNotNone(spec_sec)
        self.assertEqual(spec_sec["id"], "security_crypto_expert")

    def test_modular_architecture_scaffolder(self):
        caps = ["partita_nuova", "gioca_carta", "valuta_punteggio"]
        scaffold = project_scaffolder.scaffold_modular_architecture(
            project_name="gioco_scopa_enterprise",
            domain="gaming",
            stack={"frontend": "tsx_expert", "backend": "rust_expert", "security": "security_crypto_expert"},
            capabilities=caps,
        )

        trees = scaffold["trees"]
        self.assertIn("frontend", trees)
        self.assertIn("backend", trees)
        self.assertIn("api", trees)
        self.assertIn("mcp", trees)
        self.assertIn("security", trees)

        self.assertIn("frontend/package.json", trees["frontend"]["files"])
        self.assertIn("frontend/src/services/api_client.ts", trees["frontend"]["files"])
        self.assertIn("backend/manifest.json", trees["backend"]["files"])
        self.assertIn("api/v1/openapi.json", trees["api"]["files"])
        self.assertIn("mcp/mcp_server.json", trees["mcp"]["files"])
        self.assertIn("mcp/tools/tools_manifest.json", trees["mcp"]["files"])
        self.assertIn("security/policies/zero_trust.json", trees["security"]["files"])

        self.assertEqual(len(scaffold["api_routes"]), len(caps))
        self.assertEqual(len(scaffold["mcp_tools"]), len(caps))

        report = project_scaffolder.verify_clean_architecture(scaffold)
        self.assertTrue(report["valid"])
        self.assertTrue(report["frontend_backend_separated"])
        self.assertEqual(report["api_endpoints_count"], 3)
        self.assertEqual(report["mcp_tools_count"], 3)
        self.assertTrue(report["zero_trust_secured"])
        self.assertGreaterEqual(report["pair_desks_count"], 1)

    def test_two_agents_working_at_the_same_desk(self):
        desks = project_room.generate_autonomous_desks_and_pcs(
            called_roles=["tsx_expert", "rust_expert"],
            pair_programming=True,
        )
        self.assertGreaterEqual(len(desks), 4)
        desk_0 = desks[0]

        self.assertTrue(desk_0["is_pair_programming"])
        self.assertEqual(desk_0["kind"], "pair_collaborative")
        self.assertEqual(desk_0["capacity"], 2)
        self.assertEqual(desk_0["seat"], "dual_shared")
        self.assertEqual(desk_0["agent_id"], "tsx_expert")
        self.assertEqual(desk_0["second_agent_id"], "rust_expert")
        self.assertEqual(desk_0["agents"], ["tsx_expert", "rust_expert"])
        self.assertEqual(len(desk_0["workstations"]), 2)

        pc_primary = desk_0["workstation"]
        pc_secondary = desk_0["pc_secondary"]
        self.assertIsNotNone(pc_secondary)
        self.assertEqual(pc_primary["status"], "active")
        self.assertEqual(pc_secondary["status"], "active")
        self.assertEqual(pc_primary["assigned_worker"], "tsx_expert")
        self.assertEqual(pc_secondary["assigned_worker"], "rust_expert")

    def test_dynamic_desk_pair_assignment(self):
        desks = project_room.generate_autonomous_desks_and_pcs(["architect"])
        desk_0 = desks[0]
        self.assertFalse(desk_0["is_pair_programming"])
        self.assertEqual(len(desk_0["workstations"]), 1)

        updated = project_room.assign_pair_to_desk(desk_0, "security_crypto_expert")
        self.assertTrue(updated["is_pair_programming"])
        self.assertEqual(updated["second_agent_id"], "security_crypto_expert")
        self.assertEqual(len(updated["workstations"]), 2)
        self.assertTrue(updated["shared_screen"]["enabled"])

    async def test_tools_catalog_project_architect(self):
        ctx = Context(project_id="test_proj_p1", folder=".")

        raw_scaffold = await project_architect._scaffold_modular_project(ctx, {
            "project_name": "gestionale_fiscale_moderno",
            "domain": "finance",
            "capabilities": ["calcolo_f24", "verifica_partita_iva"],
        })
        sc_res = json.loads(raw_scaffold)
        self.assertEqual(sc_res["status"], "scaffolded")
        self.assertTrue(sc_res["verification"]["valid"])
        self.assertTrue(sc_res["verification"]["frontend_backend_separated"])

        base_room = {
            "project": {"id": "proj_pair_room_test", "title": "Stanza Pair Test"},
            "pair_programming": True,
        }
        room = project_room.build_project_room(
            base_room,
            {"id": "proj_pair_room_test", "title": "Stanza Pair Test"},
            [{"id": "html5_lead", "role": "html5_expert", "seated": True, "status": "running"}],
            {"id": "ceo", "status": "running"},
            {"rules_count": 1690, "reviews_count": 945},
        )
        self.assertEqual(room["project_id"], "proj_pair_room_test")

        raw_assign = await project_architect._assign_pair_programming_desk(ctx, {
            "project_id": "proj_pair_room_test",
            "desk_index": 0,
            "second_role": "php_expert",
        })
        assign_res = json.loads(raw_assign)
        self.assertEqual(assign_res["status"], "assigned")
        self.assertTrue(assign_res["pair_mode"])
        self.assertIn("php_expert", assign_res["agents"])
        self.assertEqual(assign_res["workstations_count"], 2)


if __name__ == "__main__":
    unittest.main()
