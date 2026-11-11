import os
import tempfile
import unittest
from pathlib import Path

from fastapi import FastAPI
from starlette.testclient import TestClient

from access import require_admin
from features.people import people
from features.people.private_store import SealedFile
from features.sentinel.api import admin_routes
from features.sentinel.privacy import export_person, privacy_overview, shred_person


class SentinelPrivacyTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        os.environ["NUXIVA_STATE_ROOT"] = str(self.root)
        people.PEOPLE_DIR = self.root / "people"
        people.PEOPLE_DIR.mkdir(parents=True, exist_ok=True)
        from cryptography.fernet import Fernet
        self.key_file = self.root / "people.key"
        self.key_file.write_bytes(Fernet.generate_key())
        import features.people.private_store as ps
        ps.KEY_FILE = self.key_file

        self.app = FastAPI()
        self.app.dependency_overrides[require_admin] = lambda: "admin"
        self.app.include_router(admin_routes)
        self.client = TestClient(self.app)

    def tearDown(self):
        self.tmp.cleanup()

    def test_privacy_overview_empty(self):
        overview = privacy_overview()
        self.assertIn("profiles", overview)
        self.assertIn("vault_days", overview)
        self.assertIn("audio_journal", overview)

    def test_privacy_overview_with_profile(self):
        p = people.ensure("alex", "Alex")
        p["consent"] = True
        p["consent_voice"] = False
        people.save(p)

        sealed = SealedFile(people.PEOPLE_DIR / "alex.private", self.key_file)
        sealed.save({"face_traits": {"glasses": True}, "gait_traits": {"cadence": 1.8}})

        overview = privacy_overview()
        found = next((item for item in overview["profiles"] if item["slug"] == "alex"), None)
        self.assertIsNotNone(found)
        self.assertEqual(found["name"], "Alex")
        self.assertTrue(found["consent"])
        self.assertFalse(found["consent_voice"])
        self.assertTrue(found["has_face_traits"])
        self.assertTrue(found["has_gait_traits"])

    def test_export_person(self):
        p = people.ensure("sam", "Sam")
        people.save(p)
        sealed = SealedFile(people.PEOPLE_DIR / "sam.private", self.key_file)
        sealed.save({"face_traits": {"beard": "none"}})

        data = export_person("sam")
        self.assertEqual(data["slug"], "sam")
        self.assertIn("profile", data)
        self.assertIn("private_biometrics", data)
        self.assertEqual(data["private_biometrics"].get("face_traits"), {"beard": "none"})

    def test_export_person_not_found_or_invalid(self):
        with self.assertRaises(ValueError):
            export_person("unknown_person")
        with self.assertRaises(ValueError):
            export_person("invalid/slug!")

    def test_shred_person(self):
        p = people.ensure("jordan", "Jordan")
        people.save(p)
        sealed = SealedFile(people.PEOPLE_DIR / "jordan.private", self.key_file)
        sealed.save({"sightings": [1, 2, 3], "face_traits": {"beard": True}})
        self.assertTrue((people.PEOPLE_DIR / "jordan.private").exists())

        receipt = shred_person("jordan")
        self.assertTrue(receipt["ok"])
        self.assertEqual(receipt["slug"], "jordan")
        self.assertIn("receipt", receipt)
        self.assertFalse((people.PEOPLE_DIR / "jordan.private").exists())

    def test_people_delete_triggers_shred(self):
        p = people.ensure("taylor", "Taylor")
        people.save(p)
        sealed = SealedFile(people.PEOPLE_DIR / "taylor.private", self.key_file)
        sealed.save({"face_traits": {"beard": False}})
        self.assertTrue((people.PEOPLE_DIR / "taylor.json").exists())
        self.assertTrue((people.PEOPLE_DIR / "taylor.private").exists())

        deleted = people.delete("taylor")
        self.assertTrue(deleted)
        self.assertFalse((people.PEOPLE_DIR / "taylor.json").exists())
        self.assertFalse((people.PEOPLE_DIR / "taylor.private").exists())

    def test_api_privacy_endpoints(self):
        p = people.ensure("morgan", "Morgan")
        people.save(p)

        res = self.client.get("/api/sentinel/privacy/overview")
        self.assertEqual(res.status_code, 200)
        self.assertIn("profiles", res.json())

        res_exp = self.client.get("/api/sentinel/privacy/export/morgan")
        self.assertEqual(res_exp.status_code, 200)
        self.assertEqual(res_exp.json()["slug"], "morgan")

        res_shred = self.client.post("/api/sentinel/privacy/shred/morgan")
        self.assertEqual(res_shred.status_code, 200)
        self.assertTrue(res_shred.json()["ok"])
        self.assertIn("receipt", res_shred.json())
