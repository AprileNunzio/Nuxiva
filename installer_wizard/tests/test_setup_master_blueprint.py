import asyncio
import os
import unittest
from pathlib import Path
from unittest import mock
from fastapi.testclient import TestClient

import nuxiva_supervisor
import setup_api
from setup_session import session_manager
from features.ear import learner as learner_module
from features.chat import speaker
from config import read_env, write_env

HEADERS = {"X-Nuxiva-Request": "1"}

class MasterBlueprintTest(unittest.TestCase):
    def setUp(self):
        self.public = TestClient(nuxiva_supervisor.public)
        session_manager.current_step = 1
        session_manager.max_reached_step = 1
        session_manager.steps_meta = {
            str(i): {"status": "active" if i == 1 else "pending", "dirty": False, "score": 100 if i == 1 else 0}
            for i in range(1, 8)
        }
        session_manager.config["assistant_name"] = "Aria"
        session_manager.config["wake_word_primary"] = "aria"
        session_manager.config["wake_phrases"] = ["aria", "ehi aria", "ok aria", "ciao aria"]
        session_manager.config["wake_phonetic_aliases"] = ["aria"]

    def tearDown(self):
        pass

    def test_session_state_machine_and_invalidation(self):
        r = self.public.get("/api/setup/session")
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertEqual(data["current_step"], 1)

        r = self.public.post("/api/setup/session/navigate", json={"target_step": 2}, headers=HEADERS)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["current_step"], 2)
        self.assertEqual(r.json()["max_reached_step"], 2)

        r = self.public.post("/api/setup/session/update", json={"step": 2, "updates": {"mic_device_id": "hw:1,0", "score": 96}}, headers=HEADERS)
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.json()["steps_meta"]["3"]["dirty"])
        self.assertTrue(r.json()["steps_meta"]["4"]["dirty"])

        r = self.public.post("/api/setup/session/navigate", json={"target_step": 1}, headers=HEADERS)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["current_step"], 1)

        r = self.public.post("/api/setup/session/update", json={"step": 1, "updates": {"locale": "en-US"}}, headers=HEADERS)
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.json()["steps_meta"]["3"]["dirty"])

        r = self.public.post("/api/setup/release-hardware", headers=HEADERS)
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.json()["ok"])

    def test_dynamic_identity_endpoint(self):
        with mock.patch.dict(os.environ, {"NUXIVA_ASSISTANT_NAME": "Atlas", "NUXIVA_WAKE_PHONETIC_ALIASES": "atlas,atlass"}):
            r = self.public.get("/api/system/identity")
            self.assertEqual(r.status_code, 200)
            data = r.json()
            self.assertEqual(data["assistant_name"], "Atlas")
            self.assertEqual(data["wake_word_primary"], "atlas")
            self.assertIn("atlas", data["wake_phonetic_aliases"])
            self.assertIn("atlass", data["wake_phonetic_aliases"])
            self.assertTrue(data["is_custom_name"])

    def test_learner_completely_excludes_nuxiva_when_renamed(self):
        with mock.patch.dict(os.environ, {"NUXIVA_ASSISTANT_NAME": "Atlas", "NUXIVA_WAKE_PHONETIC_ALIASES": "atlas,atlass"}):
            learner = learner_module.Learner()
            found_custom = learner.find_wake("Atlas accendi la luce")
            self.assertIsNotNone(found_custom)
            self.assertEqual("Atlas accendi la luce"[found_custom[1]:], "accendi la luce")

            found_alias = learner.find_wake("Ehi atlass, accendi la luce")
            self.assertIsNotNone(found_alias)
            self.assertEqual("Ehi atlass, accendi la luce"[found_alias[1]:], "accendi la luce")

            found_nuxiva = learner.find_wake("Nuxiva accendi la luce")
            self.assertIsNone(found_nuxiva)

    def test_speaker_prompt_strictly_enforces_unique_name(self):
        with mock.patch.dict(os.environ, {"NUXIVA_ASSISTANT_NAME": "Atlas"}):
            prompt = speaker.instruction()
            self.assertIn("Tu sei Atlas. Il tuo unico nome è Atlas. Non chiamarti mai Nuxiva.", prompt)

        with mock.patch.dict(os.environ, {"NUXIVA_ASSISTANT_NAME": "Nuxiva"}):
            prompt = speaker.instruction()
            self.assertIn("Tu sei Nuxiva (NUXIVA), l'assistente.", prompt)

    def test_owner_name_anti_conflict(self):
        import setup_owner
        from fastapi import HTTPException
        with self.assertRaises(HTTPException):
            setup_owner.clean_names({"name": "Atlas", "assistant_name": "Atlas"})
        with self.assertRaises(HTTPException):
            setup_owner.clean_names({"name": "Atlas", "assistant_name": "Hey Atlas"})
        first, last = setup_owner.clean_names({"name": "Nunzio", "last_name": "Rossi", "assistant_name": "Atlas"})
        self.assertEqual(first, "Nunzio")

    def test_calibration_and_telemetry_routes(self):
        r = self.public.post("/api/locale/prepare", json={"locale": "it-IT"}, headers=HEADERS)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["stt_status"], "INSTALLED_LOCAL")

        r = self.public.post("/api/cameras/scan", headers=HEADERS)
        self.assertEqual(r.status_code, 200)
        self.assertGreaterEqual(r.json()["count"], 1)

        r = self.public.post("/api/brain/benchmark", json={"preset": "nuxiva-6.5-auto"}, headers=HEADERS)
        self.assertEqual(r.status_code, 200)
        self.assertIn("ttft_ms", r.json()["benchmark"])

    def test_finalize_setup_flow(self):
        self.addCleanup(setup_api.SETUP_FILE.unlink, missing_ok=True)
        r = self.public.post("/api/setup/finalize", json={
            "assistant_name": "Atlas",
            "owner_name": "Nunzio",
            "owner_last": "Tech"
        }, headers=HEADERS)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["assistant_name"], "Atlas")
        self.assertEqual(r.json()["wake_word_primary"], "atlas")
        self.assertTrue(setup_api.done())

if __name__ == "__main__":
    unittest.main()
