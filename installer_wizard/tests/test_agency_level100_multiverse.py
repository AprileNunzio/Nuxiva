import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from agenti.agency import office
from agenti.agency.circadian import resolve_circadian_context
from agenti.agency.scanner import department_scanner
from agenti.agency.tools import Context
from agenti.agency.tools_catalog import authz, culinary, education, storytelling
from agenti.people import people, private_store


class TestAgencyLevel100Multiverse(unittest.IsolatedAsyncioTestCase):
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

    def tearDown(self):
        for p in self.patchers:
            p.stop()
        self.tmp.cleanup()

    async def test_education_modular_tools_and_socratic_guidance(self):
        ctx = Context(project_id="test_proj", folder=".")
        raw = await education._socratic_tutor_guide(ctx, {
            "topic": "Equazioni di Secondo Grado",
            "student_query": "Come trovo le soluzioni di x^2 - 5x + 6 = 0?",
            "grade_level": "media",
        })
        res = json.loads(raw)
        self.assertEqual(res["status"], "socratic_guide_ready")
        self.assertEqual(res["method"], "maieutica_socratica")
        self.assertFalse(res["direct_solution_revealed"])
        self.assertTrue(len(res["guiding_questions"]) >= 3)

        raw_simple = await education._concept_simplifier(ctx, {
            "concept": "Gravità",
            "target_age": 8,
        })
        self.assertEqual(json.loads(raw_simple)["status"], "simplified")

        specialist = department_scanner.find_specialist("Un figlio chiede aiuto con i compiti di scuola")
        self.assertIsNotNone(specialist)
        self.assertEqual(specialist["id"], "education_tutor")

    async def test_culinary_modular_tools_and_timer_sync(self):
        ctx = Context(project_id="test_proj", folder=".")
        raw_recipe = await culinary._recipe_recommender(ctx, {
            "pantry_items": ["riso carnaroli", "zucchine", "olio evo", "parmigiano"],
            "allergies": ["nichel", "crostacei"],
            "max_minutes": 25,
        })
        recipe = json.loads(raw_recipe)
        self.assertEqual(recipe["status"], "recipe_tailored")
        self.assertIn("nichel", recipe["allergen_free_guarantee"])
        self.assertTrue(recipe["prep_and_cook_minutes"] <= 25)

        raw_timer = await culinary._cooking_timer_sync(ctx, {
            "dish_name": "Risotto alle Zucchine",
            "duration_minutes": 25,
            "family_dinner_target": "20:00",
        })
        timer = json.loads(raw_timer)
        self.assertEqual(timer["recommended_start_time"], "19:35")

        raw_audit = await culinary._pantry_inventory_audit(ctx, {
            "available_items": ["farina", "uova"],
            "planned_meal": "torta_salata",
        })
        self.assertEqual(json.loads(raw_audit)["status"], "pantry_audited")

        specialist = department_scanner.find_specialist("Una mamma chiede aiuto per cucinare la cena")
        self.assertIsNotNone(specialist)
        self.assertEqual(specialist["id"], "culinary_chef")

    async def test_storytelling_modular_tools_and_ambient_preset(self):
        ctx = Context(project_id="test_proj", folder=".")
        raw_story = await storytelling._generate_bedtime_story(ctx, {
            "child_name": "Luca",
            "theme": "il bosco degli animali gentili",
            "moral": "la forza dell'amicizia",
        })
        story = json.loads(raw_story)
        self.assertEqual(story["status"], "story_generated")
        self.assertIn("Luca", story["story"])
        self.assertIn("warm_amber", story["ambient_preset"]["lighting"])
        self.assertIn("80_bpm_to_55_bpm", story["ambient_preset"]["tempo_deceleration"])

        raw_ambient = await storytelling._ambient_bedtime_preset(ctx, {
            "room": "cameretta",
            "transition_minutes": 15,
        })
        self.assertEqual(json.loads(raw_ambient)["status"], "bedtime_preset_engaged")

        specialist = department_scanner.find_specialist("Un bambino chiede una favola per dormire")
        self.assertIsNotNone(specialist)
        self.assertEqual(specialist["id"], "storyteller_kids")

    async def test_authz_modular_tools_zero_trust_and_co_presence(self):
        people.ensure("luca_child", "Luca Figlio")
        people.update("luca_child", {"role": "family", "subrole": "child"})

        people.ensure("ospite_mario", "Mario Ospite")
        people.update("ospite_mario", {"role": "guest"})

        people.ensure("nunzio_owner", "Nunzio Owner")
        people.update("nunzio_owner", {"role": "owner"})

        ctx = Context(project_id="test_proj", folder=".")

        raw_child_gate = await authz._authorize_action_by_role(ctx, {
            "person_slug": "luca_child",
            "action_kind": "gate_unlock",
        })
        self.assertFalse(json.loads(raw_child_gate)["allowed"])

        raw_child_story = await authz._authorize_action_by_role(ctx, {
            "person_slug": "luca_child",
            "action_kind": "bedtime_story",
        })
        self.assertTrue(json.loads(raw_child_story)["allowed"])

        raw_guest_fin = await authz._authorize_action_by_role(ctx, {
            "person_slug": "ospite_mario",
            "action_kind": "financial_read",
        })
        self.assertFalse(json.loads(raw_guest_fin)["allowed"])

        raw_owner_gate = await authz._authorize_action_by_role(ctx, {
            "person_slug": "nunzio_owner",
            "action_kind": "gate_unlock",
        })
        self.assertTrue(json.loads(raw_owner_gate)["allowed"])

        raw_co_eval = await authz._privacy_filter_co_presence(ctx, {
            "active_person": "nunzio_owner",
            "co_present_slugs": ["ospite_mario"],
        })
        self.assertTrue(json.loads(raw_co_eval)["masking_enforced"])

    def test_co_presence_privacy_masking_with_guests_in_room(self):
        people.ensure("nunzio", "Nunzio Aprile")
        people.update("nunzio", {"role": "owner"})

        people.ensure("ospite", "Ospite Esterno")
        people.update("ospite", {"role": "guest"})

        ctx_private = resolve_circadian_context(current_hour=10, person_slug="nunzio", co_present_slugs=[])
        self.assertFalse(ctx_private["privacy_co_presence_masked"])

        ctx_co_present = resolve_circadian_context(current_hour=10, person_slug="nunzio", co_present_slugs=["ospite"])
        self.assertTrue(ctx_co_present["privacy_co_presence_masked"])
        for widget in ctx_co_present["active_circadian_widgets"]:
            if widget.get("type") in ("market_ticker", "vitals_card"):
                self.assertIn("Discrezione Attiva", widget["title"])

        data = {"active_person": "nunzio", "co_present_slugs": ["ospite"], "project": {}}
        base = {"tasks": [], "roles": [], "tools": [], "questions": []}
        focus = office.enrich_focus(data, base)
        self.assertTrue(focus["office"]["circadian_context"]["privacy_co_presence_masked"])


if __name__ == "__main__":
    unittest.main()
