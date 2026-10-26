import sqlite3
import tempfile
import time
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest import mock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from access import require_admin
from features.habits import api as habits_api
from features.habits import service
from features.habits.journal import Journal
from features.people import schema


class JournalAttributionTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.path = Path(tmp.name) / "habits.db"
        self.journal = Journal(self.path)

    def test_events_are_attributed_filtered_and_forgotten(self):
        now = time.time()
        self.journal.add(now, "light.cucina", "on", 1, True, "action", "anna")
        self.journal.add(now, "light.sala", "on", 2, True, "action")
        self.journal.add(now, "light.studio", "on", 1, True, "action", "marco")
        self.assertEqual([r[1] for r in self.journal.rows_for("anna", now - 10)], ["light.cucina"])
        self.assertEqual(len(self.journal.rows(now - 10)), 3)
        self.assertEqual(self.journal.forget("anna"), 1)
        self.assertEqual(self.journal.rows_for("anna", now - 10), [])
        self.assertEqual(len(self.journal.rows(now - 10)), 2)

    def test_an_old_database_without_the_column_is_migrated(self):
        old = Path(self.path.parent) / "old.db"
        db = sqlite3.connect(str(old))
        db.execute("CREATE TABLE events (at REAL, entity TEXT, state TEXT, wd INTEGER, mins INTEGER, people INTEGER, sun INTEGER, kind TEXT)")
        db.execute("INSERT INTO events VALUES (1, 'light.a', 'on', 0, 0, 1, 1, 'action')")
        db.commit()
        db.close()
        journal = Journal(old)
        journal.add(2, "light.b", "on", 1, True, "action", "anna")
        self.assertEqual(journal.count(), 2)
        self.assertEqual(len(journal.rows_for("anna", 0)), 1)


class PersonHabitsTest(unittest.TestCase):
    def test_only_the_persons_own_regularities_are_returned(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        journal = Journal(Path(tmp.name) / "h.db")
        start = datetime.now().replace(hour=7, minute=30, second=0, microsecond=0) - timedelta(days=12)
        for day in range(12):
            at = (start + timedelta(days=day)).timestamp()
            journal.add(at, "light.cucina", "on", 1, True, "action", "anna")
            journal.add(at, "light.studio", "on", 1, True, "action", "marco")
            journal.add(at - 3600, "sensor.rumore", "x", 1, True, "noise", "anna")
        fake = mock.Mock(journal=journal)
        with mock.patch.object(service.bus.states, "catalog", return_value=[{"id": "light.cucina", "name": "Luce cucina"}]):
            result = service.Habits.person_habits(fake, "anna")
        self.assertEqual(result["events"], 12)
        self.assertEqual([h["entity"] for h in result["habits"]], ["light.cucina"])
        self.assertIn("Luce cucina", result["habits"][0]["text"])

    def test_route_rejects_a_hostile_slug(self):
        app = FastAPI()
        app.include_router(habits_api.admin_routes)
        app.dependency_overrides[require_admin] = lambda: "admin"
        client = TestClient(app)
        self.assertEqual(client.get("/api/habits/person/..%2Fetc").status_code, 404)
        self.assertEqual(client.get("/api/habits/person/" + "a" * 70).status_code, 400)
        with mock.patch.object(habits_api.habits, "person_habits", return_value={"events": 0, "days": 21, "habits": []}):
            self.assertEqual(client.get("/api/habits/person/anna").json()["habits"], [])


class SchemaTest(unittest.TestCase):
    def test_routine_section_holds_the_habits_without_duplicate_keys(self):
        sections = {s["id"]: s for s in schema.SECTIONS}
        routine = {f["key"] for f in sections["routine"]["fields"]}
        self.assertTrue({"wake_time", "sleep_time", "routines", "daily_habits", "quiet_hours"} <= routine)
        keys = [f["key"] for s in schema.SECTIONS for f in s["fields"]]
        self.assertEqual(len(keys), len(set(keys)))
        self.assertNotIn("habits", keys)


if __name__ == "__main__":
    unittest.main()
