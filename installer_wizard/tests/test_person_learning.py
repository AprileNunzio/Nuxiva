import tempfile
import unittest
from pathlib import Path
from unittest import mock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from access import require_admin
from features.people import insight_api, learning, mood, people, private_store


class DetectionTest(unittest.TestCase):
    def test_first_person_moods(self):
        cases = {
            "oggi sono molto stanco": ("stanco", 4),
            "mi sento un po' triste": ("triste", 2),
            "sono felice di vederti": ("felice", 3),
            "sono distrutta": ("stanco", 4),
            "ho la febbre": ("malato", 3),
            "sono davvero arrabbiato con il vicino": ("arrabbiato", 4),
        }
        for text, (name, level) in cases.items():
            with self.subTest(text=text):
                found = learning.detect_mood(text)
                self.assertEqual((found[0], found[1]), (name, level))

    def test_no_false_positives(self):
        for text in ("non sono stanco", "sei stanco?", "Marco è triste", "accendi la luce", "sono a casa", "sono stanco?"):
            with self.subTest(text=text):
                self.assertIsNone(learning.detect_mood(text))

    def test_profile_rules(self):
        found = {(i["field"], i["value"]) for i in learning.extract_profile(
            "chiamami Nunzio. Mi sveglio alle 6:30 e vado a dormire alle 23. Il caffè lo prendo amaro, tifo il Napoli")}
        self.assertEqual(found, {("nickname", "Nunzio"), ("wake_time", "06:30"), ("sleep_time", "23:00"), ("coffee", "amaro"), ("sports", "Napoli")})

    def test_invalid_values_are_dropped(self):
        self.assertEqual(learning.extract_profile("mi sveglio alle 27 di solito"), [])
        self.assertEqual(learning.extract_profile("preferisco con 80 gradi"), [])
        self.assertEqual(learning.extract_profile("che ore sono? chiamami"), [])


class LearningTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        for p in (mock.patch.object(people, "PEOPLE_DIR", root), mock.patch.object(private_store, "KEY_FILE", root / "people.key"),
                  mock.patch.object(learning.store, "event")):
            p.start()
            self.addCleanup(p.stop)
        people.ensure("anna", "Anna Rossi")

    def tearDown(self):
        self.tmp.cleanup()

    def test_observe_records_mood_and_profile(self):
        result = learning.observe("sono molto stanco, chiamami Annina", "anna")
        self.assertEqual(result["mood"]["mood"], "stanco")
        self.assertEqual(result["mood"]["source"], "assistente")
        self.assertEqual(result["mood"]["feedback"], "")
        self.assertEqual(people.load("anna")["nickname"], "Annina")
        self.assertEqual(learning.listing("anna")[0]["status"], "auto")

    def test_same_mood_is_not_repeated_within_the_window(self):
        learning.observe("sono stanco", "anna")
        self.assertIsNone(learning.observe("sono stanco morto", "anna")["mood"])
        self.assertEqual(len(mood.journal("anna")), 1)

    def test_consent_and_switch_are_respected(self):
        people.update("anna", {"consent": False})
        self.assertEqual(learning.observe("sono stanco", "anna"), {"mood": None, "profile": []})
        people.update("anna", {"consent": True})
        with mock.patch.object(learning, "env_get", return_value="0"):
            self.assertEqual(learning.observe("sono stanco", "anna"), {"mood": None, "profile": []})
        self.assertEqual(mood.journal("anna"), [])

    def test_existing_values_are_never_overwritten(self):
        people.update("anna", {"coffee": "macchiato", "music": ["Pino Daniele"]})
        learning.observe("Il caffè lo prendo amaro. Ascolto musica Pino Daniele", "anna")
        profile = people.load("anna")
        self.assertEqual(profile["coffee"], "macchiato")
        self.assertEqual(profile["music"], ["Pino Daniele"])

    def test_tags_are_appended_without_duplicates(self):
        people.update("anna", {"hobbies": ["pesca"]})
        learning.observe("la mia passione è il giardinaggio", "anna")
        learning.observe("mi appassiona giardinaggio", "anna")
        self.assertEqual(people.load("anna")["hobbies"], ["pesca", "giardinaggio"])

    def test_rejecting_reverts_and_is_remembered(self):
        learning.observe("tifo il Napoli", "anna")
        row = learning.listing("anna")[0]
        self.assertEqual(learning.feedback("anna", row["id"], "wrong")["status"], "rejected")
        self.assertEqual(people.load("anna")["sports"], [])
        self.assertEqual(learning.observe("tifo il Napoli", "anna")["profile"], [])
        self.assertEqual(people.load("anna")["sports"], [])

    def test_confirming_keeps_the_value(self):
        learning.observe("chiamami Annina", "anna")
        row = learning.listing("anna")[0]
        self.assertEqual(learning.feedback("anna", row["id"], "ok")["status"], "confirmed")
        self.assertEqual(people.load("anna")["nickname"], "Annina")
        with self.assertRaises(ValueError):
            learning.feedback("anna", row["id"], "boh")
        self.assertIsNone(learning.feedback("anna", "nope", "ok"))


class MoodFeedbackTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        for p in (mock.patch.object(people, "PEOPLE_DIR", root), mock.patch.object(private_store, "KEY_FILE", root / "people.key")):
            p.start()
            self.addCleanup(p.stop)
        people.ensure("anna", "Anna Rossi")
        self.entry = mood.record("anna", "stanco", 4, "", "assistente", "sono molto stanco")

    def tearDown(self):
        self.tmp.cleanup()

    def test_confirm(self):
        self.assertEqual(mood.feedback("anna", self.entry["id"], "ok")["feedback"], "ok")

    def test_correct(self):
        fixed = mood.feedback("anna", self.entry["id"], "wrong", "annoiato", 2)
        self.assertEqual((fixed["mood"], fixed["intensity"], fixed["source"], fixed["feedback"]), ("annoiato", 2, "persona", "corrected"))

    def test_wrong_removes_and_counts(self):
        self.assertTrue(mood.feedback("anna", self.entry["id"], "wrong")["removed"])
        self.assertEqual(mood.journal("anna"), [])
        self.assertEqual(people.load("anna")["mood_rejected"], 1)

    def test_invalid_inputs(self):
        with self.assertRaises(ValueError):
            mood.feedback("anna", self.entry["id"], "boh")
        with self.assertRaises(ValueError):
            mood.feedback("anna", self.entry["id"], "wrong", "inesistente")
        self.assertIsNone(mood.feedback("anna", "nope", "ok"))


class ApiTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        for p in (mock.patch.object(people, "PEOPLE_DIR", root), mock.patch.object(private_store, "KEY_FILE", root / "people.key"),
                  mock.patch.object(learning.store, "event"), mock.patch.object(insight_api.store, "event")):
            p.start()
            self.addCleanup(p.stop)
        people.ensure("anna", "Anna Rossi")
        app = FastAPI()
        app.include_router(insight_api.admin_routes)
        app.dependency_overrides[require_admin] = lambda: "admin"
        self.client = TestClient(app)

    def tearDown(self):
        self.tmp.cleanup()

    def test_mood_feedback_flow(self):
        entry = mood.record("anna", "stanco", 4, "", "assistente", "sono stanco")
        url = f"/api/people/anna/mood/{entry['id']}/feedback"
        self.assertEqual(self.client.post(url, json={"verdict": "boh"}).status_code, 400)
        self.assertEqual(self.client.post("/api/people/anna/mood/zzz/feedback", json={"verdict": "ok"}).status_code, 404)
        self.assertEqual(self.client.post(url, json={"verdict": "wrong", "mood": "triste", "intensity": 2}).json()["feedback"], "corrected")
        self.assertEqual(self.client.post("/api/people/nessuno/mood/x/feedback", json={"verdict": "ok"}).status_code, 404)

    def test_learned_listing_and_feedback(self):
        learning.observe("chiamami Annina", "anna")
        data = self.client.get("/api/people/anna/learned").json()
        self.assertTrue(data["enabled"])
        row = data["learned"][0]
        done = self.client.post(f"/api/people/anna/learned/{row['id']}/feedback", json={"verdict": "wrong"}).json()
        self.assertEqual(done["status"], "rejected")
        self.assertEqual(people.load("anna")["nickname"], "")
        self.assertEqual(self.client.post("/api/people/anna/learned/nope/feedback", json={"verdict": "ok"}).status_code, 404)


if __name__ == "__main__":
    unittest.main()
