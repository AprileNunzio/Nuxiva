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

    def test_database_starts_empty_without_hardcoded_profiles(self):
        self.assertIsNone(self.store.get_profile("any_user"))

    def test_autonomous_learning_from_conversational_speech(self):
        prof = self.store.learn("Mi chiamo Marco e tifo la Ferrari")
        self.assertEqual(prof.user_name, "Marco")
        self.assertIn("Ferrari", prof.interests)
        loaded = self.store.get_profile("Marco")
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded.user_name, "Marco")

    def test_update_and_retrieve_dynamic_facts(self):
        self.store.update_fact("preferred_stack", "Rust and PyTorch", "Alex")
        prof = self.store.get_profile("Alex")
        self.assertIsNotNone(prof)
        self.assertEqual(prof.facts.get("preferred_stack"), "Rust and PyTorch")

    def test_least_used_rotation(self):
        phrases = ["frase_alpha", "frase_beta", "frase_gamma"]
        chosen1 = self.store.get_least_used(phrases)
        self.assertEqual(chosen1, "frase_alpha")
        self.store.record_usage("frase_alpha", "test")
        chosen2 = self.store.get_least_used(phrases)
        self.assertNotEqual(chosen2, "frase_alpha")


class AcousticReflexEngineTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.store = ReflexMemoryStore(self.tmp / "test_engine.sqlite3")
        self.engine = AcousticReflexEngine(self.store)

    def test_anonymous_greeting_synthesizes_open_bridge(self):
        res = self.engine.evaluate("Ciao come va?", lang="it")
        self.assertEqual(res.kind, "greeting")
        self.assertFalse(res.needs_deep_reasoning)
        self.assertLess(res.latency_ms, 1000.0)
        self.assertTrue(len(res.reflex_text) > 5)

    def test_learned_user_greeting_incorporates_discovered_identity_and_passion(self):
        self.store.learn("Mi chiamo Sofia e tifo la Juventus")
        res = self.engine.evaluate("Ciao come va?", user_name="Sofia", lang="it")
        self.assertEqual(res.kind, "greeting")
        self.assertIn("Sofia", res.reflex_text)
        self.assertIn("Juventus", res.reflex_text)

    def test_executive_mode_synthesizes_operational_status(self):
        self.store.save_profile(PersonaProfile(
            user_name="Elena",
            style="executive",
            interests=[],
            facts={},
        ))
        res = self.engine.evaluate("Buongiorno", user_name="Elena", lang="it")
        self.assertEqual(res.kind, "greeting")
        self.assertIn("Elena", res.reflex_text)

    def test_complex_query_triggers_dynamic_zero_silence_filler(self):
        res = self.engine.evaluate("Analizza l'architettura dei microservizi e trova il collo di bottiglia", lang="it")
        self.assertEqual(res.kind, "thinking_filler")
        self.assertTrue(res.needs_deep_reasoning)
        self.assertLess(res.latency_ms, 1000.0)
        self.assertTrue("architettura" in res.reflex_text or "logica" in res.reflex_text)

    def test_quick_status_triggers_summary(self):
        res = self.engine.evaluate("Qual è la situazione di sistema?", lang="it")
        self.assertEqual(res.kind, "quick_status")
        self.assertFalse(res.needs_deep_reasoning)


class ReflexApiTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(nuxiva_supervisor.public)

    def test_reflex_endpoint_autonomous(self):
        res = self.client.post("/api/chat/reflex", json={"query": "Ciao come va?", "lang": "it"})
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("reflex_text", data)
        self.assertIn("latency_ms", data)
        self.assertLess(data["latency_ms"], 2000.0)

    def test_persona_learn_and_get(self):
        learn_res = self.client.post("/api/chat/learn", json={"utterance": "Mi chiamo Leonardo e lavoro su Rust"})
        self.assertEqual(learn_res.status_code, 200)
        learned = learn_res.json()
        self.assertEqual(learned["user_name"], "Leonardo")

        get_res = self.client.get("/api/chat/persona?user_name=Leonardo")
        self.assertEqual(get_res.status_code, 200)
        profile = get_res.json()
        self.assertEqual(profile["user_name"], "Leonardo")

    def test_barge_in_endpoint(self):
        res = self.client.post("/api/chat/barge_in", json={"session_id": "session_test"})
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "interrupted")
        self.assertEqual(data["session_id"], "session_test")
