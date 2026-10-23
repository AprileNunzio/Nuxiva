import io
import math
import os
from pathlib import Path
import struct
import tempfile
import unittest
import wave
from unittest import mock
from fastapi.testclient import TestClient

import nuxiva_supervisor
import setup_api
import setup_audio
import setup_routes
import setup_session
from setup_session import session_manager
from features.ear import learner as learner_module
from features.chat import speaker

HEADERS = {"X-Nuxiva-Request": "1"}


def tone(seconds: float = 1.2, rate: int = 16000, amplitude: float = 0.3, quiet: float = 0.3) -> bytes:
    frames = bytearray()
    for i in range(int(seconds * rate)):
        t = i / rate
        level = amplitude if quiet <= t <= seconds - quiet else amplitude / 400
        frames += struct.pack("<h", int(level * 32767 * math.sin(2 * math.pi * 220 * t)))
    out = io.BytesIO()
    with wave.open(out, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(rate)
        wav.writeframes(bytes(frames))
    return out.getvalue()


class MasterBlueprintTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.patches = [mock.patch.object(setup_session, "SESSION_FILE", Path(self.tmp.name) / "session.json"),
                        mock.patch.object(setup_routes, "SAMPLES_DIR", Path(self.tmp.name) / "samples"),
                        mock.patch.object(setup_api, "is_local", lambda r: True),
                        mock.patch.object(setup_api, "_private_client", lambda r: True)]
        for p in self.patches:
            p.start()
        setup_api.SETUP_FILE.unlink(missing_ok=True)
        session_manager.reset()
        self.public = TestClient(nuxiva_supervisor.public)

    def tearDown(self):
        for p in self.patches:
            p.stop()
        session_manager.reset()
        setup_api.SETUP_FILE.unlink(missing_ok=True)
        self.tmp.cleanup()

    def test_session_is_validated_persisted_privately_and_keeps_secrets_in_memory(self):
        r = self.public.get("/api/setup/session")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["current_step"], 1)
        self.assertEqual(self.public.post("/api/setup/session/navigate", json={"target_step": 3}, headers=HEADERS).status_code, 409)
        r = self.public.post("/api/setup/session/update", json={"step": 1, "updates": {"locale": "en-US"}}, headers=HEADERS)
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(r.json()["max_reached_step"], 2)
        for bad in ({"locale": "xx"}, {"is_admin": True}, {"assistant_name": "<script>"}, {"mic": {"noise_db": 5}}):
            self.assertEqual(self.public.post("/api/setup/session/update", json={"step": 2, "updates": bad},
                                              headers=HEADERS).status_code, 400, bad)
        r = self.public.post("/api/setup/session/update", json={"step": 6, "updates": {"ha_token": "a" * 40}}, headers=HEADERS)
        self.assertTrue(r.json()["secrets_set"]["ha_token"])
        stored = setup_session.SESSION_FILE.read_text(encoding="utf-8")
        self.assertNotIn("a" * 40, stored)
        if os.name != "nt":
            self.assertEqual(os.stat(setup_session.SESSION_FILE).st_mode & 0o777, 0o600)

    def test_routes_are_closed_after_setup_and_to_other_networks(self):
        with mock.patch.object(setup_api, "_private_client", lambda r: False), mock.patch.object(setup_api, "is_local", lambda r: False):
            self.assertEqual(self.public.get("/api/setup/session").status_code, 403)
        with mock.patch.object(setup_api, "done", lambda: True):
            for path in ("/api/setup/finalize", "/api/setup/session/update", "/api/setup/cameras/scan", "/api/setup/wake-sample?index=1"):
                self.assertEqual(self.public.post(path, json={}, headers=HEADERS).status_code, 410, path)
        self.assertEqual(self.public.post("/api/setup/finalize", json={}).status_code, 403)

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
        with tempfile.TemporaryDirectory() as tmp, mock.patch.dict(os.environ, {"NUXIVA_ASSISTANT_NAME": "Atlas", "NUXIVA_WAKE_PHONETIC_ALIASES": "atlas,atlass"}), mock.patch.object(learner_module, "LEARN_FILE", Path(tmp) / "learn.json"):
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
            self.assertIn("Tu sei Atlas. Il tuo unico nome è Atlas.", prompt)
        self.assertIn("Non chiamarti mai Nuxiva.", prompt)

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

    def test_wake_sample_is_measured_from_the_real_recording(self):
        session_manager.config["assistant_name"] = "Atlas"
        with mock.patch.object(learner_module.learner, "teach", return_value=True):
            r = self.public.post("/api/setup/wake-sample?index=1", content=tone(), headers={**HEADERS, "Content-Type": "audio/wav"})
        self.assertEqual(r.status_code, 200, r.text)
        data = r.json()
        self.assertTrue(data["usable"])
        self.assertGreater(data["snr_db"], 30)
        self.assertAlmostEqual(data["seconds"], 1.2, places=1)
        silent = self.public.post("/api/setup/wake-sample?index=2", content=tone(amplitude=0.0),
                                  headers={**HEADERS, "Content-Type": "audio/wav"})
        self.assertFalse(silent.json()["usable"])
        self.assertEqual(self.public.post("/api/setup/wake-sample?index=3", content=b"RIFFxxxx",
                                          headers={**HEADERS, "Content-Type": "audio/wav"}).status_code, 422)
        with self.assertRaises(setup_audio.AudioRejected):
            setup_audio.analyze(tone(seconds=0.1))

    def test_camera_scan_reports_only_found_devices(self):
        from features.cameras import discovery
        with mock.patch.object(discovery, "onvif", return_value=[]), mock.patch("setup_probe.glob.glob", return_value=[]):
            r = self.public.post("/api/setup/cameras/scan", headers=HEADERS)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["devices"], [])
        self.assertEqual(r.json()["count"], 0)

    def test_finalize_setup_flow(self):
        from features.people import people
        from config import write_env
        self.addCleanup(write_env, {"NUXIVA_UI_LANG": "it"})
        with tempfile.TemporaryDirectory() as root, mock.patch.object(people, "PEOPLE_DIR", Path(root)), \
                mock.patch.object(learner_module.learner, "teach", return_value=True):
            r = self.public.post("/api/setup/session/update", json={"step": 4, "updates": {
                "assistant_name": "Atlas", "owner_name": "Nunzio", "owner_last": "Tech", "packages": []}}, headers=HEADERS)
            self.assertEqual(r.status_code, 200, r.text)
            r = self.public.post("/api/setup/finalize", json={}, headers=HEADERS)
            self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(r.json()["assistant_name"], "Atlas")
        self.assertEqual(r.json()["wake_word_primary"], "atlas")
        self.assertTrue(setup_api.done())
        self.assertEqual(self.public.get("/api/setup/session").status_code, 410)

if __name__ == "__main__":
    unittest.main()
