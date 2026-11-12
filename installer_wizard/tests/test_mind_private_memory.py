import json
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

from cryptography.fernet import Fernet
from features.mind import memory as memory_module
from features.mind.persistence import MemoryStorageError
from features.mind.records import MemoryInputError


class PrivateMemoryTest(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.root = Path(folder.name)
        for name, path in (("MIND_DIR", self.root), ("FACTS_FILE", self.root / "facts.json"),
                           ("MEMORY_KEY", self.root / "mind.key")):
            patcher = mock.patch.object(memory_module, name, path)
            patcher.start()
            self.addCleanup(patcher.stop)
        self.memory = memory_module.LongTermMemory()

    def test_identical_fact_keeps_separate_owners_and_scopes(self):
        anna = self.memory.add("Preferisce il caffè senza zucchero", who="anna")
        luca = self.memory.add("Preferisce il caffè senza zucchero", who="luca")
        shared = self.memory.add("Preferisce il caffè senza zucchero", who="anna", scope="shared")
        self.assertEqual(len({anna["id"], luca["id"], shared["id"]}), 3)
        self.assertEqual(self.memory.add(anna["text"], who="anna")["id"], anna["id"])
        self.assertEqual({f["id"] for f in self.memory.recall("caffè", who="luca")}, {luca["id"], shared["id"]})
        self.assertEqual([f["id"] for f in self.memory.recall("caffè", who="")], [shared["id"]])

    def test_unassigned_and_expired_facts_are_never_recalled(self):
        unknown = self.memory.add("Persona allergica alle arachidi")
        expired = self.memory.add("Anna è allergica alle arachidi", who="anna", expires_at=time.time() - 1)
        self.assertEqual(unknown["scope"], "unassigned")
        for who in ("", "anna", "luca"):
            self.assertEqual(self.memory.recall("arachidi", who=who), [])
        self.assertEqual(len(self.memory.listing()), 2)
        self.assertEqual(self.memory.stats()["expired"], 1)
        self.assertTrue(self.memory.forget(expired["id"], who="anna"))

    def test_similar_contradictory_facts_require_explicit_correction(self):
        first = self.memory.add("Anna preferisce caffè senza zucchero", who="anna")
        second = self.memory.add("Anna preferisce caffè con zucchero", who="anna")
        self.assertNotEqual(first["id"], second["id"])
        revised = self.memory.update(first["id"], {"text": "Anna preferisce tè verde", "revision": 1}, who="anna")
        self.assertEqual(revised["id"], first["id"])
        self.assertEqual(revised["revision"], 2)
        self.assertEqual(revised["origin"], "manual")
        self.assertEqual(revised["history"][0]["text"], first["text"])
        with self.assertRaisesRegex(MemoryInputError, "memory_conflict"):
            self.memory.update(first["id"], {"text": "Correzione da scheda vecchia", "revision": 1}, who="anna")
        self.assertIsNone(self.memory.update(first["id"], {"text": "Non deve cambiare"}, who="luca"))
        self.assertFalse(self.memory.forget(first["id"], who="luca"))
        self.assertEqual(self.memory.listing(who="luca"), [])

    def test_correction_controls_expiry_and_sharing(self):
        fact = self.memory.add("La riunione è alle nove", who="anna")
        updated = self.memory.update(fact["id"], {"scope": "shared", "expires_at": time.time() + 60}, who="anna")
        self.assertEqual(self.memory.recall("riunione", who="luca")[0]["id"], updated["id"])
        self.memory.update(fact["id"], {"expires_at": 1}, who="anna")
        self.assertEqual(self.memory.recall("riunione", who="luca"), [])

    def test_memory_and_history_are_encrypted_and_roundtrip(self):
        fact = self.memory.add("Anna è allergica alle arachidi", who="anna", origin="manual")
        self.memory.update(fact["id"], {"text": "Anna è allergica alle noci"}, who="anna")
        path = self.root / "facts.sealed"
        self.assertFalse((self.root / "facts.json").exists())
        self.assertNotIn(b"arachidi", path.read_bytes())
        self.assertNotIn(b"noci", path.read_bytes())
        reloaded = memory_module.LongTermMemory()
        self.assertFalse(reloaded.storage_error)
        self.assertEqual(reloaded.listing(), self.memory.listing())
        returned = reloaded.listing()
        returned[0]["who"] = "luca"
        self.assertEqual(reloaded.listing()[0]["who"], "anna")

    def test_plaintext_migration_preserves_facts_and_adds_private_defaults(self):
        original = [{"id": "abc12345", "text": "Anna è allergica alle arachidi", "who": "anna", "kind": "fatto",
                     "score": 0.8, "created": 123, "updated": 456, "custom": {"preserve": True}},
                    {"id": "def12345", "text": "Un fatto senza identità", "who": "", "created": 1}]
        legacy = self.root / "facts.json"
        legacy.write_text(json.dumps(original), encoding="utf-8")
        migrated = memory_module.LongTermMemory()
        self.assertFalse(migrated.storage_error)
        self.assertFalse(legacy.exists())
        self.assertEqual(len(migrated.listing()), 2)
        anna = next(f for f in migrated.listing() if f["who"] == "anna")
        self.assertEqual(anna["custom"], {"preserve": True})
        self.assertEqual((anna["created"], anna["updated"], anna["origin"]), (123, 456, "legacy"))
        self.assertEqual(migrated.recall("senza identità", who="luca"), [])

    def test_corrupt_plaintext_is_preserved_and_visible(self):
        legacy = self.root / "facts.json"
        legacy.write_text("{broken", encoding="utf-8")
        broken = memory_module.LongTermMemory()
        self.assertTrue(broken.stats()["storage_error"])
        self.assertEqual(legacy.read_text(encoding="utf-8"), "{broken")
        with self.assertRaises(MemoryStorageError):
            broken.add("Non deve sovrascrivere i dati", who="anna")
        self.assertFalse((self.root / "facts.sealed").exists())

    def test_missing_or_wrong_key_never_overwrites_ciphertext(self):
        self.memory.add("Segreto personale da conservare", who="anna")
        encrypted = (self.root / "facts.sealed").read_bytes()
        key = self.root / "mind.key"
        key.unlink()
        broken = memory_module.LongTermMemory()
        self.assertEqual(broken.storage_error, "encryption_key_missing")
        self.assertFalse(key.exists())
        with self.assertRaises(MemoryStorageError):
            broken.clear()
        key.write_bytes(Fernet.generate_key())
        broken = memory_module.LongTermMemory()
        self.assertTrue(broken.storage_error)
        with self.assertRaises(MemoryStorageError):
            broken.add("Nuovi dati non devono sostituire i vecchi", who="anna")
        self.assertEqual((self.root / "facts.sealed").read_bytes(), encrypted)

    def test_failed_save_preserves_previous_in_memory_and_disk_state(self):
        fact = self.memory.add("Ricordo originale da preservare", who="anna")
        original = (self.root / "facts.sealed").read_bytes()
        with mock.patch.object(self.memory.storage, "save", side_effect=MemoryStorageError("storage_write_failed")):
            with self.assertRaises(MemoryStorageError):
                self.memory.update(fact["id"], {"text": "Correzione da non perdere"}, who="anna")
        self.assertEqual(self.memory.facts[0]["text"], fact["text"])
        self.assertEqual((self.root / "facts.sealed").read_bytes(), original)

    def test_invalid_metadata_cannot_change_a_record(self):
        fact = self.memory.add("Un ricordo personale valido", who="anna")
        for changes in ({"scope": []}, {"expires_at": "nan"}, {"expires_at": True}, {"who": "luca"},
                        {"text": {}}, {"revision": True}, {"origin": "manual"}):
            with self.subTest(changes=changes), self.assertRaises(MemoryInputError):
                self.memory.update(fact["id"], changes, who="anna")
        self.assertEqual(self.memory.listing()[0]["revision"], 1)

    def test_diary_migration_encrypts_personal_utterances_too(self):
        from features.mind import mind as mind_module
        legacy = self.root / "mind.json"
        legacy.write_text(json.dumps({"diary": [{"said": "La mia allergia alle arachidi"}]}), encoding="utf-8")
        with mock.patch.object(mind_module, "MIND_DIR", self.root), mock.patch.object(mind_module, "STATE_FILE", legacy):
            mind = mind_module.Mind()
        self.assertFalse(mind.storage_error)
        self.assertFalse(legacy.exists())
        self.assertNotIn(b"arachidi", (self.root / "mind.sealed").read_bytes())
        self.assertEqual(mind.diary[0]["said"], "La mia allergia alle arachidi")


if __name__ == "__main__":
    unittest.main()
