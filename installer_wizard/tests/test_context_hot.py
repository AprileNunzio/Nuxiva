import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from agenti.people import hot, mood, people, private_store

try:
    import nuxiva_native
except ImportError:
    nuxiva_native = None

NATIVE = nuxiva_native is not None and hasattr(nuxiva_native, "RustUserContext")


class HotContextBase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        for patch in (
            mock.patch.object(people, "PEOPLE_DIR", root),
            mock.patch.object(private_store, "KEY_FILE", root / "people.key"),
            mock.patch.dict(os.environ, {"NUXIVA_CONTEXT_ENGINE": "rust"}),
        ):
            patch.start()
            self.addCleanup(patch.stop)
        hot.reset()
        self.addCleanup(hot.reset)
        self.addCleanup(self.tmp.cleanup)

    def family(self):
        people.ensure("anna", "Anna Rossi")
        people.update("anna", {"role": "family", "nickname": "Nan", "occupation": "ingegnera", "music": ["jazz"],
                               "food_likes": ["salato"], "allergies": ["funghi"], "diet": "Vegetariana",
                               "coffee": "senza zucchero", "birthday": "1990-05-02"})
        people.ensure("luca", "Luca Bianchi")
        people.update("luca", {"role": "family", "relations": [{"type": "fratello", "person": "anna"}]})
        people.update("anna", {"share_health": True})
        people.ensure("ospite-1", "Ospite Uno")


@unittest.skipUnless(NATIVE, "modulo nativo non installato")
class HotContextTest(HotContextBase):
    def test_every_fact_of_the_text_oracle_reaches_the_family_view(self):
        self.family()
        oracle = people.context_for(["anna"])
        hot_text = hot.context_for(["anna"])
        for fact in ("Anna Rossi", "Nan", "ingegnera", "jazz", "salato", "funghi", "Vegetariana", "senza zucchero"):
            self.assertIn(fact, oracle)
            self.assertIn(fact, hot_text)

    def test_a_guest_in_the_room_hides_personal_details(self):
        self.family()
        text = hot.context_for(["anna", "ospite-1"], subjects=["anna"])
        self.assertIn("Anna Rossi", text)
        for secret in ("funghi", "jazz", "ingegnera", "Vegetariana"):
            self.assertNotIn(secret, text)

    def test_updates_and_deletions_reach_the_hot_memory_without_reload(self):
        self.family()
        self.assertIn("jazz", hot.context_for(["anna"]))
        people.update("anna", {"music": ["rock"]})
        text = hot.context_for(["anna"])
        self.assertIn("rock", text)
        self.assertNotIn("jazz", text)
        people.delete("anna")
        self.assertEqual(hot.context_for(["anna"]), "")

    def test_withdrawn_consent_hides_the_person(self):
        self.family()
        hot.context_for(["anna"])
        people.update("anna", {"consent": False})
        self.assertEqual(hot.context_for(["anna"]), "")

    def test_the_latest_mood_is_included(self):
        self.family()
        mood.record("anna", "felice", 4, "", "manuale")
        self.assertIn("umore", hot.context_for(["anna"]))

    def test_unknown_people_are_ignored(self):
        self.family()
        self.assertEqual(hot.context_for(["nessuno"]), "")


class FallbackTest(HotContextBase):
    def test_python_engine_keeps_the_text_oracle(self):
        self.family()
        with mock.patch.dict(os.environ, {"NUXIVA_CONTEXT_ENGINE": "python"}):
            self.assertEqual(hot.context_for(["anna"]), people.context_for(["anna"]))

    def test_sensitive_data_stay_out_of_the_enriched_payload(self):
        self.family()
        people.update("anna", {"biography": "Nata a Napoli"})
        payload = hot.enrich(people.load("anna"), {})
        self.assertNotIn("biography", payload)
        self.assertNotIn("voice", payload)
        self.assertNotIn("sessions", payload)
