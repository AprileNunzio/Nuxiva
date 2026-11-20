import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from agenti.agency import circadian, office
from agenti.agency.circadian import (
    CircadianHabitTracker,
    PHASE_EVENING,
    PHASE_MARKET,
    PHASE_MORNING,
    PHASE_NIGHT,
    PHASE_PROJECTS,
    compute_current_phase,
    resolve_circadian_context,
)
from agenti.agency.scanner import department_scanner
from agenti.agency.tools import Context
from agenti.agency.tools_catalog import people_adapter
from agenti.people import people, private_store


class TestAgencyPersonHabits(unittest.IsolatedAsyncioTestCase):
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

    def test_multi_person_circadian_adaptation(self):
        p_nunzio = people.ensure("nunzio", "Nunzio Aprile")
        people.update("nunzio", {
            "wake_time": "06:00",
            "sleep_time": "23:00",
            "coffee": "espresso amaro",
            "hobbies": ["intelligenza artificiale", "finanza"],
            "movies": ["fantascienza", "cyberpunk"],
        })

        p_angelika = people.ensure("angelika", "Angelika Aprile")
        people.update("angelika", {
            "wake_time": "08:30",
            "sleep_time": "00:30",
            "coffee": "cappuccino con avena",
            "hobbies": ["interior design", "musica classica"],
            "movies": ["commedie romantiche", "documentari"],
        })

        ctx_nunzio_7am = resolve_circadian_context(current_hour=7, person_slug="nunzio")
        self.assertEqual(ctx_nunzio_7am["phase"], PHASE_MORNING)
        self.assertIn("espresso amaro", json.dumps(ctx_nunzio_7am["active_circadian_widgets"]))
        self.assertIn("Nunzio", ctx_nunzio_7am["circadian_greeting"])

        ctx_angelika_7am = resolve_circadian_context(current_hour=7, person_slug="angelika")
        self.assertEqual(ctx_angelika_7am["phase"], PHASE_NIGHT)

        ctx_angelika_9am = resolve_circadian_context(current_hour=9, person_slug="angelika")
        self.assertEqual(ctx_angelika_9am["phase"], PHASE_MORNING)
        self.assertIn("cappuccino con avena", json.dumps(ctx_angelika_9am["active_circadian_widgets"]))
        self.assertIn("Angelika", ctx_angelika_9am["circadian_greeting"])

        ctx_nunzio_evening = resolve_circadian_context(current_hour=21, person_slug="nunzio")
        self.assertEqual(ctx_nunzio_evening["phase"], PHASE_EVENING)
        self.assertIn("fantascienza", json.dumps(ctx_nunzio_evening["active_circadian_widgets"]))

        ctx_angelika_evening = resolve_circadian_context(current_hour=22, person_slug="angelika")
        self.assertEqual(ctx_angelika_evening["phase"], PHASE_EVENING)
        self.assertIn("commedie romantiche", json.dumps(ctx_angelika_evening["active_circadian_widgets"]))

    def test_person_habit_tracker_per_individual(self):
        tracker = CircadianHabitTracker()
        tracker.record_interaction(10, "stock_ticker", person_slug="nunzio")
        tracker.record_interaction(10, "stock_ticker", person_slug="nunzio")
        tracker.record_interaction(10, "design_board", person_slug="angelika")
        tracker.record_interaction(10, "design_board", person_slug="angelika")

        self.assertEqual(tracker.top_habit_for_hour(10, person_slug="nunzio"), "stock_ticker")
        self.assertEqual(tracker.top_habit_for_hour(10, person_slug="angelika"), "design_board")

    async def test_multimodal_perception_learning_and_storage(self):
        people.ensure("angelika", "Angelika Aprile")
        ctx = Context(project_id="test_p", folder=".")

        raw_result = await people_adapter._perceive_multimodal_person(ctx, {
            "visual_cue": "Angelika sorridente davanti alla postazione",
            "spoken_text": "La mia abitudine è yoga e adoro guardare fantascienza",
        })
        res = json.loads(raw_result)
        self.assertEqual(res["active_person"], "angelika")

        profile = people.load("angelika")
        self.assertIn("yoga", profile.get("daily_habits") or [])
        self.assertIn("fantascienza", profile.get("movies") or [])

    async def test_get_and_update_person_preference_tools(self):
        ctx = Context(project_id="test_p", folder=".")
        update_res = await people_adapter._update_person_preference(ctx, {
            "slug": "nunzio",
            "field": "coffee",
            "value": "ristretto macchiato freddo",
        })
        self.assertEqual(json.loads(update_res)["status"], "saved")

        get_res = await people_adapter._get_person_profile(ctx, {"slug": "nunzio"})
        profile_data = json.loads(get_res)
        self.assertEqual(profile_data["tastes"]["coffee"], "ristretto macchiato freddo")

    def test_department_scanner_specialist_dispatch_people_butler(self):
        specialist = department_scanner.find_specialist("Adatta le abitudini e i gusti per la singola persona")
        self.assertIsNotNone(specialist)
        self.assertEqual(specialist["id"], "people_butler")
        self.assertIn("person-profiling", specialist["skills"])

    def test_office_enrich_focus_integrates_active_person(self):
        people.ensure("nunzio", "Nunzio Aprile")
        data = {"active_person": "nunzio", "project": {}}
        base = {"tasks": [], "roles": [], "tools": [], "questions": []}
        focus = office.enrich_focus(data, base)
        self.assertEqual(focus["office"]["active_person"], "nunzio")
        circ = focus["office"]["circadian_context"]
        self.assertEqual(circ["person_slug"], "nunzio")
        self.assertIn("Nunzio", circ["circadian_greeting"])


if __name__ == "__main__":
    unittest.main()
