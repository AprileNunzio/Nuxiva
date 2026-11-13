import json
import os
import time
import unittest
from unittest import mock

from agenti.people import hot, people, percept
from tests.test_context_hot import HotContextBase

try:
    import nuxiva_native
except ImportError:
    nuxiva_native = None

NATIVE = nuxiva_native is not None and hasattr(nuxiva_native, "RustPercept")


@unittest.skipUnless(NATIVE, "modulo nativo non installato")
class PerceptNativeTest(HotContextBase):
    def setUp(self):
        super().setUp()
        percept.reset()
        self.addCleanup(percept.reset)
        self.family()

    def test_known_speaker_with_allergy_reaches_the_answer_context(self):
        text = percept.context_for("cosa cucino stasera", ["anna"], speaker="anna")
        self.assertIn("funghi", text)
        self.assertIn("Anna Rossi", text)

    def test_guest_present_hides_personal_data_of_everyone(self):
        text = percept.context_for("cosa cucino stasera", ["anna", "ospite-1"], speaker="anna")
        self.assertIn("Anna Rossi", text)
        for secret in ("funghi", "jazz", "ingegnera", "Vegetariana", "Luca"):
            self.assertNotIn(secret, text)

    def test_unknown_person_present_is_treated_as_outsider(self):
        text = percept.context_for("ciao", ["anna", "sconosciuto"], speaker="anna")
        for secret in ("funghi", "jazz", "ingegnera"):
            self.assertNotIn(secret, text)

    def test_expired_emotion_is_not_presented_as_current(self):
        now = int(time.time() * 1000)
        percept.from_mood("anna", 0.9, 0.8, now_ms=now)
        fresh = percept.context_for("ciao", ["anna"], speaker="anna")
        old = now - 3_600_000
        with mock.patch.object(percept.time, "time", return_value=(old + 7_200_000) / 1000):
            percept.from_mood("anna", 0.9, 0.8, now_ms=old)
            stale = percept.context_for("ciao", ["anna"], speaker="anna")
        self.assertNotIn("energ", stale.lower())
        self.assertIsInstance(fresh, str)

    def test_invalid_observation_is_rejected_and_reply_falls_back(self):
        with self.assertRaises(ValueError):
            percept._fusion().observe(json.dumps({"kind": "speaker", "person": "anna", "permille": 5000, "at_ms": 1}), 1)
        with self.assertRaises(ValueError):
            percept._fusion().observe(json.dumps({"kind": "bogus"}), 1)
        self.assertIn("Anna Rossi", percept.context_for("x", ["anna"], speaker="Non Valido!"))

    def test_disabled_engine_falls_back_to_the_text_view(self):
        with mock.patch.dict(os.environ, {"NUXIVA_CONTEXT_ENGINE": "python"}):
            self.assertEqual(percept.context_for("x", ["anna"], speaker="anna"), people.context_for(["anna"]))
