from pathlib import Path
import tempfile
import unittest

from fastapi.testclient import TestClient

import nuxiva_supervisor
from features.chat.reflex_engine import AcousticReflexEngine
from features.chat.reflex_memory import PersonaProfile, ReflexMemoryStore


class ReflexMemoryTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.store = ReflexMemoryStore(self.tmp / "test_reflex.sqlite3")

    def test_default_profile_created(self):
        prof = self.store.get_profile("Nunzio")
        self.assertIsNotNone(prof)
        self.assertEqual(prof.user_name, "Nunzio")
        self.assertIn("napoli_calcio", prof.interests)

    def test_update_and_retrieve_facts(self):
        self.store.update_fact("napoli_status", "Vittoria 3-0 contro la Juventus", "Nunzio")
        prof = self.store.get_profile("Nunzio")
        self.assertEqual(prof.facts.get("napoli_status"), "Vittoria 3-0 contro la Juventus")

    def test_least_used_rotation(self):
        phrases = ["frase_a", "frase_b", "frase_c"]
        chosen1 = self.store.get_least_used(phrases)
        self.assertEqual(chosen1, "frase_a")
        self.store.record_usage("frase_a", "test")
        chosen2 = self.store.get_least_used(phrases)
        self.assertNotEqual(chosen2, "frase_a")


class AcousticReflexEngineTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.store = ReflexMemoryStore(self.tmp / "test_engine.sqlite3")
        self.engine = AcousticReflexEngine(self.store)

    def test_greeting_triggers_instant_napoli_response(self):
        res = self.engine.evaluate("Ciao Jarvis come va?", user_name="Nunzio", lang="it")
        self.assertEqual(res.kind, "greeting")
        self.assertFalse(res.needs_deep_reasoning)
        self.assertLess(res.latency_ms, 50.0)
        self.assertTrue("Napoli" in res.reflex_text or "Nunzio" in res.reflex_text)

    def test_executive_greeting_triggers_work_status(self):
        self.store.save_profile(PersonaProfile(
            user_name="Nunzio",
            style="executive",
            interests=["devops", "kubernetes"],
            facts={},
        ))
        res = self.engine.evaluate("Buongiorno Jarvis", user_name="Nunzio", lang="it")
        self.assertEqual(res.kind, "greeting")
        self.assertIn("direttive", res.reflex_text.lower())

    def test_complex_query_triggers_thinking_filler(self):
        res = self.engine.evaluate("Analizza l'architettura dei microservizi e trova il collo di bottiglia", user_name="Nunzio", lang="it")
        self.assertEqual(res.kind, "thinking_filler")
        self.assertTrue(res.needs_deep_reasoning)
        self.assertLess(res.latency_ms, 50.0)
        self.assertIn("Nunzio", res.reflex_text)

    def test_quick_status_triggers_summary(self):
        res = self.engine.evaluate("Qual è la situazione di sistema?", user_name="Nunzio", lang="it")
        self.assertEqual(res.kind, "quick_status")
        self.assertFalse(res.needs_deep_reasoning)


class ReflexApiTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(nuxiva_supervisor.public)

    def test_reflex_endpoint(self):
        res = self.client.post("/api/chat/reflex", json={"query": "Ciao come va?", "user_name": "Nunzio", "lang": "it"})
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("reflex_text", data)
        self.assertIn("latency_ms", data)
        self.assertLess(data["latency_ms"], 100.0)

    def test_persona_get_and_update(self):
        res = self.client.get("/api/chat/persona?user_name=Nunzio")
        self.assertEqual(res.status_code, 200)
        orig = res.json()
        self.assertEqual(orig["user_name"], "Nunzio")

        update_res = self.client.post("/api/chat/persona", json={
            "user_name": "Nunzio",
            "style": "entertaining",
            "interests": ["napoli_calcio", "musica"],
            "facts": {"napoli_status": "Vittoria storica al Maradona"},
        })
        self.assertEqual(update_res.status_code, 200)
        updated = update_res.json()
        self.assertEqual(updated["style"], "entertaining")
        self.assertEqual(updated["facts"]["napoli_status"], "Vittoria storica al Maradona")

    def test_barge_in_endpoint(self):
        res = self.client.post("/api/chat/barge_in", json={"session_id": "test_sess"})
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "interrupted")
        self.assertEqual(data["session_id"], "test_sess")
