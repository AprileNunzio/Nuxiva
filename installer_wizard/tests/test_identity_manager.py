import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from sealed import SealedFile

from access import require_admin
from agenti.people import api as people_api
from agenti.people import learning, mood, people, private_store
from agenti.people.mentions import Mentions
from agenti.people.vitals.history import DAYS, History


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        for p in (mock.patch.object(people, "PEOPLE_DIR", root), mock.patch.object(private_store, "KEY_FILE", root / "people.key")):
            p.start()
            self.addCleanup(p.stop)


class MentionsTest(Base):
    def test_unique_names_are_attributed_and_ambiguous_ones_are_not(self):
        people.ensure("anna-rossi", "Anna Rossi")
        people.ensure("marco-bianchi", "Marco Bianchi")
        people.ensure("marco-verdi", "Marco Verdi")
        found = Mentions()
        self.assertEqual(found.owner("Anna è allergica alle noci"), "anna-rossi")
        self.assertEqual(found.owner("A Marco piace il jazz"), "")
        self.assertEqual(found.owner("Marco Verdi tifa per il Napoli"), "marco-verdi")
        self.assertEqual(found.owner("Annamaria non c'entra"), "")
        self.assertEqual(found.owner("Anna e Marco Verdi partono"), "")
        self.assertEqual(found.owner("Anna ama il mare", speaker="anna-rossi"), "")

    def test_guests_are_never_matched(self):
        people.ensure("ospite-1", "Ospite 1")
        self.assertEqual(Mentions().find("Ospite 1 è arrivato"), [])


class RetentionTest(Base):
    def test_learned_facts_are_kept_and_rejected_ones_go_first(self):
        profile = {"learned": [{"id": "r", "status": "rejected"}] + [{"id": str(i), "status": "auto"} for i in range(3)]}
        with mock.patch.object(learning, "MAX_LEARNED", 3):
            learning._log(profile, {"field": "music", "kind": "tags", "value": "jazz", "evidence": "x"})
        ids = [r["id"] for r in profile["learned"]]
        self.assertNotIn("r", ids)
        self.assertEqual(len(ids), 3)

    def test_old_moods_are_archived_by_month(self):
        people.ensure("anna", "Anna Rossi")
        with mock.patch.object(mood, "MAX_ENTRIES", 2):
            for i in range(4):
                mood.record("anna", "felice", 3, at=time.time() - (10 - i) * 86400)
        profile = people.load("anna")
        self.assertEqual(len(profile["mood_journal"]), 2)
        self.assertEqual(sum(sum(b.values()) for b in profile["mood_archive"].values()), 2)

    def test_health_days_fold_into_months_forever(self):
        root = Path(self.tmp.name)
        history = History(SealedFile(root / "h.vault", root / "h.key"))
        start = time.time() - (DAYS + 40) * 86400
        for d in range(DAYS + 40):
            ts = start + d * 86400
            history.record("anna", {"metric": "weight", "value": 70.0, "ts": ts}, "scale", "ble", ts)
        span = history.span("anna")
        self.assertEqual(span["days"], DAYS)
        self.assertGreaterEqual(span["months"], 1)
        self.assertEqual(history.months("anna", "weight")[0]["value"], 70.0)


class OverviewApiTest(Base):
    def test_overview_summarises_every_section(self):
        people.ensure("anna", "Anna Rossi")
        app = FastAPI()
        app.include_router(people_api.admin_routes)
        app.dependency_overrides[require_admin] = lambda: "admin"
        client = TestClient(app)
        with mock.patch.object(people_api, "FACES", Path(self.tmp.name)):
            body = client.get("/api/people/anna/overview").json()
        self.assertEqual((body["first_name"], body["last_name"]), ("Anna", "Rossi"))
        self.assertIn("identity", body["sections"])
        self.assertGreaterEqual(body["sections"]["identity"]["filled"], 1)
        for key in ("health", "mood", "memories", "learned", "habits", "connectors", "face", "voice"):
            self.assertIn(key, body)
        self.assertEqual(client.get("/api/people/nessuno/overview").status_code, 404)
