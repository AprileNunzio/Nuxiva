import unittest

from agenti.agency.circadian import (
    PHASE_EVENING,
    PHASE_MARKET,
    PHASE_MORNING,
    PHASE_PROJECTS,
    compute_current_phase,
    get_habit_tracker,
    resolve_circadian_context,
)
from agenti.agency.office import enrich_focus


class TestAgencyCircadian(unittest.TestCase):
    def test_circadian_phases_by_hour(self):
        self.assertEqual(compute_current_phase(7), PHASE_MORNING)
        self.assertEqual(compute_current_phase(10), PHASE_MARKET)
        self.assertEqual(compute_current_phase(15), PHASE_PROJECTS)
        self.assertEqual(compute_current_phase(21), PHASE_EVENING)

    def test_circadian_context_resolution(self):
        ctx_morning = resolve_circadian_context(current_hour=7)
        self.assertEqual(ctx_morning["phase"], PHASE_MORNING)
        titles_m = [w["title"] for w in ctx_morning["active_circadian_widgets"]]
        self.assertTrue(any("Sonno" in t or "Vitali" in t for t in titles_m))

        ctx_market = resolve_circadian_context(current_hour=10)
        self.assertEqual(ctx_market["phase"], PHASE_MARKET)
        titles_f = [w["title"] for w in ctx_market["active_circadian_widgets"]]
        self.assertTrue(any("Borsa" in t for t in titles_f))

        ctx_projects = resolve_circadian_context(current_hour=14)
        self.assertEqual(ctx_projects["phase"], PHASE_PROJECTS)
        titles_p = [w["title"] for w in ctx_projects["active_circadian_widgets"]]
        self.assertTrue(any("Progetti" in t for t in titles_p))

        ctx_evening = resolve_circadian_context(current_hour=21)
        self.assertEqual(ctx_evening["phase"], PHASE_EVENING)
        titles_e = [w["title"] for w in ctx_evening["active_circadian_widgets"]]
        self.assertTrue(any("TV" in t or "Film" in t for t in titles_e))

    def test_autonomous_habit_learning(self):
        tracker = get_habit_tracker()
        for _ in range(5):
            tracker.record_interaction(21, "netflix_thriller_movies")
        top_habit = tracker.top_habit_for_hour(21)
        self.assertEqual(top_habit, "netflix_thriller_movies")

        ctx = resolve_circadian_context(current_hour=21)
        self.assertEqual(ctx["learned_preference"], "netflix_thriller_movies")
        first_widget = ctx["active_circadian_widgets"][0]
        self.assertEqual(first_widget["type"], "learned_habit")
        self.assertIn("Netflix Thriller Movies", first_widget["title"])

    def test_enrich_focus_exposes_circadian_morphing(self):
        base = {
            "id": "p_circadian",
            "goal": "Gestione intelligente orari",
            "status": "running",
            "roles": [{"id": "customer", "mission": "Supporto"}],
            "tasks": [],
            "tools": [],
        }
        res = enrich_focus({"project": {"title": "Maggiordomo Circadiano"}}, base)
        office = res["office"]
        self.assertIn("circadian_context", office)
        circ = office["circadian_context"]
        self.assertIn("phase", circ)
        self.assertIn("active_circadian_widgets", circ)
        self.assertEqual(circ["butler_mode"], "proactive_morphing")
