import asyncio
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from access import require_admin
from features.people import people, private_store
from features.people.wellbeing import api as wb_api
from features.people.wellbeing import protocol, report, safety, scoring, service, store


def run(coro):
    return asyncio.run(coro)


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        patches = (mock.patch.object(store, "FILE", root / "w.db"), mock.patch.object(people, "PEOPLE_DIR", root),
                   mock.patch.object(private_store, "KEY_FILE", root / "people.key"), mock.patch.object(wb_api.events, "event"))
        for p in patches:
            p.start()
            self.addCleanup(p.stop)
        store._consent.clear()
        store._ready.clear()
        store._last_reading.clear()
        service._saved.clear()
        scoring.meter.forget("anna")
        people.ensure("anna", "Anna Rossi")
        self.addCleanup(self.tmp.cleanup)


RAW = {"width": 0.5, "drop": 0.6, "brow": 0.2, "mimic": 0.01}


class ScoringTest(unittest.TestCase):
    def warm(self, **kw):
        base = scoring.Baseline()
        for i in range(60):
            base.update({k: v + (0.001 if i % 2 else -0.001) for k, v in RAW.items()})
        return base

    def test_tension_when_brow_and_mimic_spike(self):
        out = scoring.score({**RAW, "brow": 0.45, "mimic": 0.05, "width": 0.45, "drop": 0.66}, self.warm())
        self.assertEqual(out["area"], "tension")
        self.assertGreater(out["arousal"], 66)

    def test_exhaustion_when_everything_is_flat(self):
        out = scoring.score({**RAW, "brow": 0.05, "mimic": 0.0, "width": 0.46, "drop": 0.62}, self.warm())
        self.assertEqual(out["area"], "exhaustion")

    def test_relief_with_a_smile_and_relaxed_brow(self):
        out = scoring.score({**RAW, "width": 0.56, "drop": 0.54, "brow": 0.19, "mimic": 0.012}, self.warm())
        self.assertEqual(out["area"], "relief")

    def test_baseline_is_receptive_and_calibration_flag(self):
        meter = scoring.LiveMeter()
        first = meter.ingest("x", RAW, 1.0)
        self.assertTrue(first["calibrating"])
        self.assertEqual(first["area"], "receptive")

    def test_live_average_expires(self):
        meter = scoring.LiveMeter()
        meter.ingest("x", RAW, 1.0)
        self.assertIsNotNone(meter.live("x", 5.0))
        self.assertIsNone(meter.live("x", 500.0))

    def test_areas_cover_the_four_macro_zones(self):
        self.assertEqual({scoring.classify(80, -0.5), scoring.classify(10, -0.1), scoring.classify(40, 0.0), scoring.classify(40, 0.6)},
                         set(scoring.AREAS))


class SafetyTest(unittest.TestCase):
    def test_detects_crisis_in_every_language(self):
        for text in ("a volte penso di farla finita", "I want to kill myself", "je veux me tuer", "quiero matarme", "voglio morire"):
            self.assertTrue(safety.detect(text), text)

    def test_ordinary_sentences_are_not_flagged(self):
        for text in ("sono stanco morto dal lavoro", "I killed it at the presentation", "ho dormito male"):
            self.assertFalse(safety.detect(text), text)

    def test_response_has_local_resources(self):
        self.assertIn("112", safety.response("it"))
        self.assertIn("3114", safety.response("fr"))
        self.assertIn("024", safety.response("es"))
        self.assertIn("988", safety.response("de"))


class ProtocolTest(unittest.TestCase):
    def test_phases(self):
        self.assertEqual(protocol.phase_for(0, None, 0, 10), "opening")
        self.assertEqual(protocol.phase_for(0, None, 3, 10), "central")
        self.assertEqual(protocol.phase_for(0, None, 0, 400), "central")
        self.assertEqual(protocol.phase_for(0, 100, 9, 100 + 36 * 60), "closing")
        self.assertEqual(protocol.phase_for(0, 100, 9, 200, closing=True), "closing")
        self.assertTrue(protocol.nearing_end(100, 100 + 31 * 60))
        self.assertFalse(protocol.nearing_end(100, 100 + 10 * 60))

    def test_stage_progression(self):
        self.assertEqual(protocol.advance("assessment", 2, False), ("assessment", False))
        self.assertEqual(protocol.advance("assessment", 3, False), ("treatment", False))
        self.assertEqual(protocol.advance("treatment", 8, False), ("treatment", False))
        self.assertEqual(protocol.advance("treatment", 8, True), ("consolidation", False))
        self.assertEqual(protocol.advance("treatment", 12, False), ("consolidation", False))
        self.assertEqual(protocol.advance("consolidation", 6, False), ("consolidation", True))

    def test_intervals_thin_out(self):
        self.assertEqual(protocol.next_interval("treatment", 3), 7 * 86400)
        self.assertEqual(protocol.next_interval("consolidation", 1), 14 * 86400)
        self.assertEqual(protocol.next_interval("consolidation", 3), 30 * 86400)


class StoreTest(Base):
    def test_text_is_encrypted_at_rest(self):
        store.set_consent("anna", True)
        session = store.new_session("anna", "assessment", "it", 5, 100.0)
        store.add_turn(session["id"], "user", "opening", "frase segretissima", 101.0)
        raw = store.FILE.read_bytes()
        self.assertNotIn(b"segretissima", raw)
        self.assertEqual(store.turns(session["id"])[0]["text"], "frase segretissima")
        self.assertEqual(oct(store.FILE.stat().st_mode & 0o777), "0o600")

    def test_erase_removes_everything(self):
        store.set_consent("anna", True)
        session = store.new_session("anna", "assessment", "it", None, 100.0)
        store.add_turn(session["id"], "user", "opening", "x", 101.0)
        store.save_summary(session["id"], {"summary": "s"})
        store.add_reading("anna", {"arousal": 50.0, "area": "receptive"}, 100.0)
        service.forget("anna")
        with sqlite3.connect(store.FILE) as db:
            counts = [db.execute(f"select count(*) from {t}").fetchone()[0] for t in ("sessions", "turns", "summaries", "readings", "consent")]
        self.assertEqual(counts, [0, 0, 0, 0, 0])

    def test_readings_are_rate_limited(self):
        reading = {"arousal": 50.0, "area": "receptive"}
        self.assertTrue(store.add_reading("anna", reading, 100.0))
        self.assertFalse(store.add_reading("anna", reading, 110.0))
        self.assertTrue(store.add_reading("anna", reading, 140.0))


class FlowTest(Base):
    def setUp(self):
        super().setUp()
        patch = mock.patch.object(service, "llm", new=mock.AsyncMock(return_value="Come ti senti?"))
        self.llm = patch.start()
        self.addCleanup(patch.stop)

    def test_consent_is_required(self):
        with self.assertRaises(PermissionError):
            run(service.start("anna", "it"))

    def test_session_flow_and_plan(self):
        store.set_consent("anna", True)
        started = run(service.start("anna", "it", 4, 1000.0))
        sid = started["id"]
        self.assertEqual(started["turns"][0]["role"], "assistant")
        self.assertTrue(run(service.start("anna", "it", 4, 1001.0))["resumed"])
        for i in range(3):
            out = run(service.turn("anna", sid, f"messaggio {i}", 1010.0 + i))
        self.assertEqual(out["phase"], "central")
        self.llm.return_value = {"summary": "Ha parlato di lavoro", "themes": ["lavoro"], "reported": ["dorme poco"], "for_professional": ["sonno"]}
        closed = run(service.close("anna", sid, 7, 2000.0))
        self.assertEqual(closed["summary"]["themes"], ["lavoro"])
        self.assertEqual(closed["plan"]["stage"], "assessment")
        self.assertAlmostEqual(closed["plan"]["next_at"], 2000.0 + 7 * 86400)
        self.assertIsNone(store.open_session("anna"))

    def test_crisis_bypasses_the_model_and_flags_the_session(self):
        store.set_consent("anna", True)
        sid = run(service.start("anna", "it", None, 1000.0))["id"]
        self.llm.reset_mock()
        out = run(service.turn("anna", sid, "a volte penso di farla finita", 1010.0))
        self.assertTrue(out["crisis"])
        self.assertIn("112", out["reply"])
        self.llm.assert_not_called()
        self.assertEqual(store.session(sid)["risk"], 1)

    def test_stage_advances_after_three_sessions(self):
        store.set_consent("anna", True)
        for i in range(3):
            sid = run(service.start("anna", "it", None, 1000.0 + i * 10000))["id"]
            run(service.turn("anna", sid, "ciao", 1001.0 + i * 10000))
            run(service.close("anna", sid, None, 1500.0 + i * 10000))
        self.assertEqual(store.plan("anna")["stage"], "treatment")

    def test_unknown_session_and_empty_text(self):
        store.set_consent("anna", True)
        with self.assertRaises(LookupError):
            run(service.turn("anna", "nope", "x"))
        sid = run(service.start("anna", "it"))["id"]
        with self.assertRaises(ValueError):
            run(service.turn("anna", sid, "   "))

    def test_model_unavailable_uses_the_fallback(self):
        from features.brain.llm import BrainUnavailable
        self.llm.side_effect = BrainUnavailable("x")
        store.set_consent("anna", True)
        started = run(service.start("anna", "en"))
        self.assertIn("Anna", started["turns"][0]["text"])

    def test_ingest_stores_readings_only_with_consent_and_after_calibration(self):
        for i in range(scoring.WARM_SAMPLES + 2):
            service.ingest("anna", RAW, 100.0 + i * 31)
        self.assertEqual(store.readings("anna"), [])
        store.set_consent("anna", True)
        service.ingest("anna", RAW, 5000.0)
        self.assertEqual(len(store.readings("anna")), 1)


class ReportTest(Base):
    def test_report_contains_disclaimer_digest_and_optional_transcript(self):
        store.set_consent("anna", True)
        with mock.patch.object(service, "llm", new=mock.AsyncMock(return_value="ok")):
            sid = run(service.start("anna", "it", 3, 1000.0))["id"]
            run(service.turn("anna", sid, "dormo male", 1010.0))
            run(service.close("anna", sid, 6, 1900.0))
        plain = report.build("anna", "it", now=2000.0)
        self.assertIn("NON è una diagnosi", plain["disclaimer"])
        self.assertEqual(plain["sessions"][0]["mood_before"], 3)
        self.assertNotIn("transcript", plain["sessions"][0])
        full = report.build("anna", "it", True, now=2000.0)
        self.assertEqual(full["sessions"][0]["transcript"][1]["text"], "dormo male")
        self.assertIn("NON è una diagnosi", report.markdown(full))


class ApiTest(Base):
    def setUp(self):
        super().setUp()
        app = FastAPI()
        app.include_router(wb_api.admin_routes)
        app.dependency_overrides[require_admin] = lambda: "admin"
        self.client = TestClient(app)
        patch = mock.patch.object(service, "llm", new=mock.AsyncMock(return_value="Dimmi di più"))
        patch.start()
        self.addCleanup(patch.stop)

    def test_consent_then_session_then_report(self):
        self.assertEqual(self.client.post("/api/people/anna/wellbeing/sessions", json={}).status_code, 403)
        self.assertEqual(self.client.put("/api/people/anna/wellbeing/consent", json={"active": "si"}).status_code, 400)
        self.assertTrue(self.client.put("/api/people/anna/wellbeing/consent", json={"active": True}).json()["consent"])
        sid = self.client.post("/api/people/anna/wellbeing/sessions", json={"lang": "it"}).json()["id"]
        turn = self.client.post(f"/api/people/anna/wellbeing/sessions/{sid}/turn", json={"text": "ciao"})
        self.assertEqual(turn.json()["reply"], "Dimmi di più")
        self.assertEqual(self.client.post(f"/api/people/anna/wellbeing/sessions/{sid}/turn", json={"text": ""}).status_code, 400)
        self.assertEqual(self.client.post("/api/people/anna/wellbeing/sessions/zz/turn", json={"text": "x"}).status_code, 404)
        self.assertEqual(self.client.post(f"/api/people/anna/wellbeing/sessions/{sid}/close", json={"mood_after": 8}).status_code, 200)
        self.assertIn("Anna", self.client.get("/api/people/anna/wellbeing/report?format=md&lang=it").text)
        self.assertTrue(self.client.delete("/api/people/anna/wellbeing").json()["erased"])
        self.assertFalse(self.client.get("/api/people/anna/wellbeing").json()["consent"])

    def test_unknown_person(self):
        self.assertEqual(self.client.get("/api/people/nessuno/wellbeing").status_code, 404)


if __name__ == "__main__":
    unittest.main()
