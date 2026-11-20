import unittest

from agenti.agency import office
from agenti.agency.project_room import (
    generate_autonomous_desks_and_pcs,
    get_project_room,
    list_project_rooms,
)


class TestAgencyProjectRooms(unittest.TestCase):
    def test_autonomous_creation_of_desks_and_pcs(self):
        called = ["architect", "backend", "frontend"]
        desks = generate_autonomous_desks_and_pcs(called)

        self.assertGreaterEqual(len(desks), 4)
        for d in desks:
            self.assertIn("pc", d)
            self.assertIn("workstation", d)
            pc = d["pc"]
            self.assertIn("pc_id", pc)
            self.assertIn("hostname", pc)
            self.assertIn("status", pc)

        occupied = [d for d in desks if d["occupied"]]
        self.assertEqual(len(occupied), 3)
        self.assertEqual(occupied[0]["pc"]["status"], "active")
        self.assertEqual(occupied[0]["agent_id"], "architect")

        standby = [d for d in desks if not d["occupied"]]
        self.assertEqual(standby[0]["pc"]["status"], "standby")

    def test_room_dimensions_scale_with_called_agents(self):
        few_desks = generate_autonomous_desks_and_pcs(["worker_1", "worker_2"])
        many_desks = generate_autonomous_desks_and_pcs([f"worker_{i}" for i in range(14)])

        self.assertGreaterEqual(len(many_desks), 14)
        self.assertGreater(len(many_desks), len(few_desks))

    def test_every_project_is_an_autonomous_room(self):
        data = {
            "project": {
                "id": "proj_ecommerce_2026",
                "title": "Nuovo E-Commerce Enterprise",
                "goal": "Sviluppo backend server e microservizi per pagamenti",
            }
        }
        base = {
            "id": "proj_ecommerce_2026",
            "title": "Nuovo E-Commerce Enterprise",
            "status": "running",
            "roles": [{"id": "backend", "mission": "Sviluppo API"}],
            "tasks": [{"id": "t1", "title": "Setup DB", "role": "backend", "status": "running"}],
            "tools": ["python", "docker"],
            "questions": [],
        }

        focus = office.enrich_focus(data, base)
        office_data = focus["office"]

        self.assertIn("room", office_data)
        room = office_data["room"]

        self.assertEqual(room["project_id"], "proj_ecommerce_2026")
        self.assertEqual(room["room_id"], "room_proj_ecommerce_2026")
        self.assertIn("E-Commerce", room["name"])
        self.assertEqual(room["theme"], "cyber_minimal_glass")
        self.assertGreater(room["dimensions"]["floor_area_sqm"], 50)
        self.assertEqual(len(room["seated_agents"]), 1)
        self.assertEqual(room["seated_agents"][0]["role"], "backend")

        saved = get_project_room("proj_ecommerce_2026")
        self.assertIsNotNone(saved)
        self.assertEqual(saved["room_id"], "room_proj_ecommerce_2026")

        all_rooms = list_project_rooms()
        self.assertTrue(any(r["project_id"] == "proj_ecommerce_2026" for r in all_rooms))

    def test_multiple_projects_form_distinct_rooms(self):
        data_fin = {
            "project": {
                "id": "proj_fintech_hub",
                "title": "Trading Bot AI",
                "goal": "Analisi borsa e trading criptovalute",
            }
        }
        base_fin = {
            "id": "proj_fintech_hub",
            "status": "running",
            "roles": [{"id": "quant_analyst", "mission": "Strategie borsa"}],
            "tasks": [{"id": "t2", "title": "Backtest", "role": "quant_analyst", "status": "running"}],
            "tools": ["pandas"],
            "questions": [],
        }
        focus_fin = office.enrich_focus(data_fin, base_fin)
        room_fin = focus_fin["office"]["room"]

        data_edu = {
            "project": {
                "id": "proj_kids_tutor",
                "title": "Doposcuola Socratico",
                "goal": "Supporto compiti e lezioni scolastiche",
            }
        }
        base_edu = {
            "id": "proj_kids_tutor",
            "status": "running",
            "roles": [{"id": "education_tutor", "mission": "Guida didattica"}],
            "tasks": [{"id": "t3", "title": "Compiti mate", "role": "education_tutor", "status": "running"}],
            "tools": [],
            "questions": [],
        }
        focus_edu = office.enrich_focus(data_edu, base_edu)
        room_edu = focus_edu["office"]["room"]

        self.assertNotEqual(room_fin["room_id"], room_edu["room_id"])
        self.assertEqual(room_fin["theme"], "fintech_war_room")
        self.assertEqual(room_edu["theme"], "socratic_academy_lab")


if __name__ == "__main__":
    unittest.main()
