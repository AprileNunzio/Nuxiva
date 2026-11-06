import io
import math
import os
import struct
import tempfile
import unittest
import wave
from pathlib import Path
from unittest import mock

from fastapi.testclient import TestClient

import nuxiva_supervisor
import setup_api
import setup_audio
import setup_routes
import setup_session
from features.ear import learner as learner_module
from setup_session import session_manager

HEADERS = {"X-Nuxiva-Request": "1"}
WAV = {**HEADERS, "Content-Type": "audio/wav"}


def take(seconds=1.6, rate=16000, amplitude=0.3, lead=0.4, tail=0.4, clip=False):
    frames = bytearray()
    for i in range(int(seconds * rate)):
        t = i / rate
        level = amplitude if lead <= t <= seconds - tail else amplitude / 400
        value = int(level * 32767 * math.sin(2 * math.pi * 220 * t))
        if clip:
            value = 32767 if value >= 0 else -32768
        frames += struct.pack("<h", value)
    out = io.BytesIO()
    with wave.open(out, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(bytes(frames))
    return out.getvalue()


def native_available():
    try:
        import nuxiva_native
    except ImportError:
        return False
    return hasattr(nuxiva_native, "voice_take_check")


class SetupVoiceTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.patches = [mock.patch.object(setup_session, "SESSION_FILE", Path(self.tmp.name) / "session.json"),
                        mock.patch.object(setup_routes, "SAMPLES_DIR", Path(self.tmp.name) / "samples"),
                        mock.patch.object(setup_api, "_private_client", lambda r: True),
                        mock.patch.object(learner_module.learner, "teach", return_value=True)]
        for p in self.patches:
            p.start()
        setup_api.SETUP_FILE.unlink(missing_ok=True)
        session_manager.reset()
        session_manager.config["assistant_name"] = ""
        self.client = TestClient(nuxiva_supervisor.public)

    def tearDown(self):
        for p in self.patches:
            p.stop()
        session_manager.reset()
        self.tmp.cleanup()

    def test_mic_calibration_is_validated_strictly(self):
        body = {"noise_db": -62.4, "voice_db": -21.0, "snr_db": 41.4, "sample_rate": 48000, "device": "USB Mic",
                "gain_db": 18, "echo": True, "noise": "yes"}
        r = self.client.post("/api/setup/mic", json=body, headers=HEADERS)
        self.assertEqual(r.status_code, 200, r.text)
        mic = r.json()["mic"]
        self.assertEqual((mic["gain_db"], mic["echo"], mic["noise"]), (18.0, True, False))
        self.assertEqual(session_manager.config["mic"]["sample_rate"], 48000)
        for bad in ([], {"noise_db": "x"}, "nope", {**body, "gain_db": 99}, {**body, "snr_db": "nan"}):
            self.assertEqual(self.client.post("/api/setup/mic", json=bad, headers=HEADERS).status_code, 400, bad)
        self.assertEqual(self.client.post("/api/setup/mic", content=b"{" * 5000, headers={**HEADERS, "Content-Type": "application/json"}).status_code, 413)
        self.assertEqual(self.client.post("/api/setup/mic", json=body).status_code, 403)

    def test_assistant_name_is_saved_before_wake_takes(self):
        r = self.client.post("/api/setup/wake-sample?index=1", content=take(), headers=WAV)
        self.assertEqual(r.status_code, 409)
        self.assertEqual(self.client.post("/api/setup/assistant", json={"name": "<script>"}, headers=HEADERS).status_code, 400)
        r = self.client.post("/api/setup/assistant", json={"name": "Atlas"}, headers=HEADERS)
        self.assertEqual(r.json(), {"assistant_name": "Atlas", "wake_word": "atlas"})
        r = self.client.post("/api/setup/wake-sample?index=1", content=take(), headers=WAV)
        self.assertEqual(r.status_code, 200, r.text)
        data = r.json()
        self.assertTrue(data["usable"])
        self.assertEqual(data["word"], "atlas")
        self.assertIn("engine", data)
        self.assertEqual(session_manager.config["wake_samples"]["1"]["usable"], True)

    def test_every_take_gets_a_technical_verdict_on_both_engines(self):
        engines = [("0", "python")]
        if native_available():
            engines.append(("auto", "rust"))
        for flag, engine in engines:
            with self.subTest(engine=engine), mock.patch.dict(os.environ, {"NUXIVA_NATIVE": flag}):
                good = setup_audio.analyze(take())
                self.assertEqual((good["engine"], good["usable"], good["reason"]), (engine, True, ""))
                clipped = setup_audio.analyze(take(amplitude=1.0, clip=True))
                self.assertFalse(clipped["usable"])
                self.assertIn("clipped", clipped["reasons"])
                silent = setup_audio.analyze(take(amplitude=0.0))
                self.assertFalse(silent["usable"])
                for key in ("speech_db", "noise_db", "peak_db", "snr_db", "clipped_pct", "sample_rate"):
                    self.assertIn(key, good)

    @unittest.skipUnless(native_available(), "nuxiva_native not built")
    def test_rust_check_reports_edges_and_suggested_gain(self):
        report = setup_audio.analyze(take(amplitude=0.02, lead=0.02, tail=0.4))
        self.assertIn("truncated", report["reasons"])
        self.assertTrue(report["usable"])
        self.assertGreater(report["gain_db"], 0)
        self.assertLessEqual(report["gain_db"], 24)
        for key in ("voiced_seconds", "lead_s", "tail_s", "score", "dc_offset"):
            self.assertIn(key, report)


if __name__ == "__main__":
    unittest.main()
