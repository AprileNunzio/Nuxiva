import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from features.people import mood, people, private_store


class PeoplePrivateTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        patches = [mock.patch.object(people, "PEOPLE_DIR", root), mock.patch.object(private_store, "KEY_FILE", root / "people.key")]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)
        self.root = root

    def tearDown(self):
        self.tmp.cleanup()

    def test_private_fields_are_encrypted_at_rest(self):
        people.ensure("anna", "Anna Rossi")
        people.update("anna", {"allergies": ["arachidi"], "biography": "Nata a Napoli", "nickname": "Annina"})
        plain = (self.root / "anna.json").read_text(encoding="utf-8")
        self.assertNotIn("arachidi", plain)
        self.assertNotIn("Napoli", plain)
        self.assertIn("Annina", plain)
        self.assertNotIn(b"arachidi", (self.root / "anna.private").read_bytes())
        self.assertEqual((self.root / "anna.json").stat().st_mode & 0o777, 0o600)
        loaded = people.load("anna")
        self.assertEqual(loaded["allergies"], ["arachidi"])
        self.assertEqual(loaded["biography"], "Nata a Napoli")
        people.delete("anna")
        self.assertFalse((self.root / "anna.private").exists())

    def test_legacy_plaintext_moves_to_sealed_file(self):
        (self.root / "luca.json").write_text(json.dumps({"slug": "luca", "name": "Luca", "allergies": ["polline"]}), encoding="utf-8")
        people.save(people.load("luca"))
        self.assertNotIn("polline", (self.root / "luca.json").read_text(encoding="utf-8"))
        self.assertEqual(people.load("luca")["allergies"], ["polline"])

    def test_voice_update_is_restricted(self):
        people.ensure("anna", "Anna")
        with self.assertRaises(ValueError):
            people.update("anna", {"voice": {"tts_voice": "voce-inesistente"}})
        people.update("anna", {"voice": {"speed": 9, "voiceprint": "hack"}})
        voice = people.load("anna")["voice"]
        self.assertEqual(voice["speed"], 2.0)
        self.assertIsNone(voice.get("voiceprint"))

    def test_mood_journal(self):
        people.ensure("anna", "Anna")
        entry = mood.record("anna", "felice", 4, "promozione al lavoro <b>", "manuale")
        self.assertEqual(mood.latest("anna")["id"], entry["id"])
        self.assertNotIn("promozione", (self.root / "anna.json").read_text(encoding="utf-8"))
        for bad in (("gioioso", 3), ("felice", 0), ("felice", "x")):
            with self.assertRaises(ValueError):
                mood.record("anna", *bad)
        self.assertTrue(mood.remove("anna", entry["id"]))
        self.assertEqual(mood.journal("anna"), [])
        with self.assertRaises(KeyError):
            mood.record("ghost", "felice")


if __name__ == "__main__":
    unittest.main()
