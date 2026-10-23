import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from features.people import learning, mood, panel, people, private_store


class PanelTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        for p in (mock.patch.object(people, "PEOPLE_DIR", root), mock.patch.object(private_store, "KEY_FILE", root / "people.key"),
                  mock.patch.object(learning.store, "event"), mock.patch.object(panel.store, "event")):
            p.start()
            self.addCleanup(p.stop)
        people.ensure("anna", "Anna Rossi")
        people.ensure("marco", "Marco Bianchi")
        app = FastAPI()
        app.include_router(panel.public_routes)
        self.client = TestClient(app)
        self.addCleanup(self.tmp.cleanup)

    def get(self, **params):
        with mock.patch.object(panel, "require_display"):
            return self.client.get("/api/display/people-panel", params=params)

    def test_roster_marks_visible_and_recent_people_at_home(self):
        people.observe("marco", "Marco Bianchi", time.time() - 7200)
        visible = [{"known": True, "slug": "anna", "near": True}]
        with mock.patch.object(panel, "visible_people", return_value=visible):
            data = self.get().json()
        rows = {r["slug"]: r for r in data["roster"]}
        self.assertTrue(rows["anna"]["home"])
        self.assertFalse(rows["marco"]["home"])
        self.assertEqual(rows["anna"]["initials"], "AR")
        self.assertEqual(data["focus"]["slug"], "anna")

    def test_focus_carries_mood_series_and_learned(self):
        learning.observe("sono molto stanco, tifo il Napoli", "anna")
        with mock.patch.object(panel, "visible_people", return_value=[{"known": True, "slug": "anna"}]):
            focus = self.get().json()["focus"]
        self.assertEqual(focus["mood"]["mood"], "stanco")
        self.assertEqual(len(focus["series"]), 7)
        self.assertEqual(focus["series"][-1]["mood"], "stanco")
        self.assertEqual({r["field"] for r in focus["learned"]}, {"sports"})

    def test_no_focus_when_nobody_is_visible(self):
        with mock.patch.object(panel, "visible_people", return_value=[]):
            self.assertIsNone(self.get().json()["focus"])

    def test_requested_focus_must_be_visible(self):
        visible = [{"known": True, "slug": "anna"}]
        with mock.patch.object(panel, "visible_people", return_value=visible):
            self.assertEqual(self.get(focus="marco").json()["focus"]["slug"], "anna")

    def feedback(self, body, header=True):
        headers = {"X-Nuxiva-Request": "1"} if header else {}
        with mock.patch.object(panel, "require_display"):
            return self.client.post("/api/display/people-panel/feedback", json=body, headers=headers)

    def test_feedback_confirms_and_rejects(self):
        learning.observe("sono molto stanco, tifo il Napoli", "anna")
        entry = mood.latest("anna")
        self.assertEqual(self.feedback({"kind": "mood", "slug": "anna", "id": entry["id"], "verdict": "ok"}).status_code, 200)
        self.assertEqual(mood.latest("anna")["feedback"], "ok")
        row = learning.listing("anna")[0]
        self.assertEqual(self.feedback({"kind": "learned", "slug": "anna", "id": row["id"], "verdict": "wrong"}).status_code, 200)
        self.assertEqual(learning.listing("anna")[0]["status"], "rejected")

    def test_feedback_needs_csrf_header_and_valid_input(self):
        self.assertEqual(self.feedback({"kind": "mood", "slug": "anna", "id": "x", "verdict": "ok"}, header=False).status_code, 403)
        self.assertEqual(self.feedback({"kind": "boh", "slug": "anna", "id": "x", "verdict": "ok"}).status_code, 400)
        self.assertEqual(self.feedback({"kind": "mood", "slug": "nessuno", "id": "x", "verdict": "ok"}).status_code, 404)
        self.assertEqual(self.feedback({"kind": "mood", "slug": "anna", "id": "x", "verdict": "ok"}).status_code, 404)
        self.assertEqual(self.feedback({"kind": "mood", "slug": "anna", "id": "x", "verdict": "forse"}).status_code, 400)
        self.assertEqual(self.feedback({"kind": "mood", "slug": "anna", "id": "x" * 900, "verdict": "ok"}).status_code, 413)


if __name__ == "__main__":
    unittest.main()
