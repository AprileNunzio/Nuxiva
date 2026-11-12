import tempfile
import unittest
from pathlib import Path
from unittest import mock

import numpy as np
from fastapi import FastAPI
from fastapi.testclient import TestClient

from features.ear import api as ear_api
from features.ear import journal as journal_module
from features.ear import journal_api

PEOPLE = [{"slug": "anna", "name": "Anna Rossi"}, {"slug": "marco", "name": "Marco Bianchi"}]


class JournalApiTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.log = journal_module.Journal(Path(self.tmp.name) / "j")
        patches = (mock.patch.object(journal_api, "journal", self.log), mock.patch.object(journal_api, "require_admin"),
                   mock.patch.object(journal_api, "household", return_value=PEOPLE),
                   mock.patch.object(journal_api, "LINK_FILE", Path(self.tmp.name) / "none.json"),
                   mock.patch.object(journal_api.store, "event"))
        for patch in patches:
            patch.start()
            self.addCleanup(patch.stop)
        app = FastAPI()
        app.include_router(ear_api.admin_routes)
        self.client = TestClient(app)
        audio = (np.sin(np.linspace(0, 100, 16000)) * 0.3).astype(np.float32)
        self.entry = self.log.record("heard", "che bella giornata", "it", "anna", 0.7, audio=audio)

    def test_list_returns_entries_stats_people_and_live_state(self):
        data = self.client.get("/api/ear/journal").json()
        self.assertEqual(data["items"][0]["text"], "che bella giornata")
        self.assertEqual(data["stats"]["total"], 1)
        self.assertEqual(data["people"], PEOPLE)
        self.assertFalse(data["live"]["available"])

    def test_filters_and_bad_values(self):
        self.assertEqual(self.client.get("/api/ear/journal?kind=command").json()["items"], [])
        self.assertEqual(self.client.get("/api/ear/journal?q=bella").json()["items"][0]["id"], self.entry)
        self.assertEqual(self.client.get("/api/ear/journal?limit=abc").status_code, 400)

    def test_audio_is_served_as_wav(self):
        response = self.client.get(f"/api/ear/journal/{self.entry}/audio")
        self.assertEqual(response.headers["content-type"], "audio/wav")
        self.assertTrue(response.content.startswith(b"RIFF"))
        self.assertEqual(self.client.get("/api/ear/journal/000000000000/audio").status_code, 404)
        self.assertEqual(self.client.get("/api/ear/journal/..%2Fx/audio").status_code, 404)

    def test_feedback_validates_person_and_verdict(self):
        url = f"/api/ear/journal/{self.entry}/feedback"
        self.assertEqual(self.client.post(url, json={"verdict": "wrong", "speaker": "marco", "correction": "che bella serata"}).status_code, 200)
        self.assertEqual(self.log.get(self.entry)["fix_speaker"], "marco")
        self.assertEqual(self.client.post(url, json={"verdict": "wrong", "speaker": "intruso"}).status_code, 400)
        self.assertEqual(self.client.post(url, json={"verdict": "boh"}).status_code, 404)
        self.assertEqual(self.client.post("/api/ear/journal/zz/feedback", json={"verdict": "ok"}).status_code, 400)

    def test_delete_and_purge(self):
        self.assertEqual(self.client.delete(f"/api/ear/journal/{self.entry}").status_code, 200)
        self.assertEqual(self.client.delete(f"/api/ear/journal/{self.entry}").status_code, 404)
        self.log.record("heard", "altro")
        self.assertEqual(self.client.post("/api/ear/journal/purge").json()["removed"], 1)

    def test_display_config_exposes_caption_settings(self):
        with mock.patch.object(ear_api, "require_display"), mock.patch.object(ear_api, "speaker_names", return_value={"anna": "Anna"}), \
                mock.patch.dict("os.environ", {"NUXIVA_CAPTIONS_SIZE": "large", "NUXIVA_CAPTIONS_HOLD": "99"}):
            app = FastAPI()
            app.include_router(ear_api.public_routes)
            data = TestClient(app).get("/api/ear/config").json()
        self.assertEqual(data["captions"]["size"], "large")
        self.assertEqual(data["captions"]["hold"], 30.0)
        self.assertEqual(data["speakers"], {"anna": "Anna"})


if __name__ == "__main__":
    unittest.main()
