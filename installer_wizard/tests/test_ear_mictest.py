import asyncio
import io
import os
import tempfile
import unittest
import wave
from unittest import mock

import numpy as np

from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from features.ear import api as ear_api
from features.ear import equalizer, levels, micsource, mictest, mictest_api

RATE = 16000


def tone(freq: float, level: float, seconds: float = 1.0) -> np.ndarray:
    t = np.arange(int(RATE * seconds)) / RATE
    return (np.sin(2 * np.pi * freq * t) * level).astype(np.float32)


def band_rms(x: np.ndarray) -> float:
    core = x[RATE // 10:-RATE // 10]
    return float(np.sqrt(np.mean(core * core)))


def chain(eq: equalizer.EqSettings | None = None) -> mictest.Chain:
    return mictest.Chain(eq=eq or equalizer.EqSettings(), target_rms=0.075, max_gain=30.0, wake_gain_limit=8.0,
                         autotuned=False)


class EqualizerTest(unittest.TestCase):
    def test_disabled_equalizer_is_bit_exact(self):
        x = tone(440, 0.2)
        out = equalizer.apply(x, equalizer.EqSettings(enabled=False, low_db=12))
        self.assertTrue(np.array_equal(out, x))

    def test_highpass_removes_rumble_and_keeps_voice(self):
        eq = equalizer.EqSettings(enabled=True, highpass_hz=150)
        rumble = equalizer.apply(tone(50, 0.2), eq)
        voice = equalizer.apply(tone(1000, 0.2), eq)
        self.assertLess(band_rms(rumble), band_rms(tone(50, 0.2)) * 0.15)
        self.assertGreater(band_rms(voice), band_rms(tone(1000, 0.2)) * 0.95)

    def test_bands_boost_and_cut_their_region(self):
        eq = equalizer.EqSettings(enabled=True, low_db=-12, high_db=6)
        low = band_rms(equalizer.apply(tone(80, 0.05), eq)) / band_rms(tone(80, 0.05))
        high = band_rms(equalizer.apply(tone(7000, 0.05), eq)) / band_rms(tone(7000, 0.05))
        self.assertLess(low, 0.4)
        self.assertGreater(high, 1.6)

    def test_settings_are_clamped_and_reject_garbage(self):
        eq = equalizer.EqSettings.build("1", "9000", "-99", "abc", "nan")
        self.assertEqual(eq, equalizer.EqSettings(enabled=True, highpass_hz=300.0, low_db=-12.0, mid_db=0.0, high_db=0.0))

    def test_settings_read_from_environment(self):
        values = {"NUXIVA_EAR_EQ": "1", "NUXIVA_EAR_EQ_HIGHPASS": "120", "NUXIVA_EAR_EQ_MID": "3,5"}
        with mock.patch.dict(os.environ, values):
            eq = equalizer.EqSettings.from_env()
        self.assertTrue(eq.active)
        self.assertEqual((eq.highpass_hz, eq.mid_db), (120.0, 3.5))

    def test_output_never_exceeds_full_scale(self):
        out = equalizer.apply(tone(1000, 0.9), equalizer.EqSettings(enabled=True, mid_db=12))
        self.assertLessEqual(float(np.abs(out).max()), 1.0)


class LevelsTest(unittest.TestCase):
    def test_judge_matches_autolevel_thresholds(self):
        self.assertEqual(levels.judge(0.5, 0.0), "lower")
        self.assertEqual(levels.judge(0.1, 0.05), "lower")
        self.assertEqual(levels.judge(0.005, 0.0), "raise")
        self.assertEqual(levels.judge(0.08, 0.0), "ok")

    def test_utterance_gain_is_bounded(self):
        self.assertEqual(levels.utterance_gain(np.zeros(RATE, dtype=np.float32), 0.075, 30), 1.0)
        self.assertLessEqual(levels.utterance_gain(tone(300, 0.004), 0.075, 30), 30)
        self.assertLess(levels.utterance_gain(tone(300, 0.6) * np.linspace(0.2, 1.0, RATE, dtype=np.float32), 0.075, 30), 1.0)


class MicTestAnalysisTest(unittest.TestCase):
    def pcm(self, x: np.ndarray) -> bytes:
        return np.round(np.clip(x, -1, 32767 / 32768) * 32768).astype("<i2").tobytes()

    def speech_like(self, level: float) -> np.ndarray:
        rng = np.random.default_rng(7)
        noise = rng.standard_normal(RATE * 5).astype(np.float32) * 0.001
        voice = np.concatenate([np.zeros(RATE * 2), tone(400, level, 3.0)]).astype(np.float32)
        return noise + voice

    def test_meter_zones(self):
        self.assertEqual(mictest.meter(np.zeros(800, dtype=np.float32))["zone"], "silent")
        self.assertEqual(mictest.meter(tone(400, 0.008)[:800])["zone"], "quiet")
        self.assertEqual(mictest.meter(tone(400, 0.1)[:800])["zone"], "good")
        self.assertEqual(mictest.meter(np.ones(800, dtype=np.float32))["zone"], "clip")

    def test_quiet_microphone_is_amplified_and_flagged(self):
        report, raw, processed = mictest.analyze(self.pcm(self.speech_like(0.01)), chain())
        self.assertEqual(report["verdict"], "raise")
        self.assertGreater(report["wake_gain"], 2.0)
        self.assertGreater(report["phrase_gain"], 2.0)
        self.assertEqual(report["seconds"], 5.0)
        self.assertEqual(len(report["timeline"]), 100)
        with wave.open(io.BytesIO(raw)) as wav:
            self.assertEqual((wav.getframerate(), wav.getnchannels(), wav.getnframes()), (RATE, 1, RATE * 5))
        self.assertGreater(len(processed), 44)

    def test_clipping_microphone_asks_to_lower(self):
        report, _, _ = mictest.analyze(self.pcm(self.speech_like(1.4)), chain())
        self.assertEqual(report["verdict"], "lower")
        self.assertLess(report["wake_gain"], 1.0)

    def test_good_level_and_silence(self):
        self.assertEqual(mictest.analyze(self.pcm(self.speech_like(0.08)), chain())[0]["verdict"], "ok")
        self.assertEqual(mictest.analyze(bytes(RATE * 2), chain())[0]["verdict"], "silent")

    def test_report_carries_the_equalizer_used(self):
        eq = equalizer.EqSettings(enabled=True, highpass_hz=100)
        report, _, _ = mictest.analyze(self.pcm(self.speech_like(0.08)), chain(eq))
        self.assertEqual(report["eq"]["highpass_hz"], 100.0)


class MicSourceTest(unittest.TestCase):
    def script(self, body: str) -> list[list[str]]:
        handle = tempfile.NamedTemporaryFile("w", suffix=".sh", delete=False)
        handle.write("#!/bin/sh\n" + body + "\n")
        handle.close()
        os.chmod(handle.name, 0o700)
        self.addCleanup(os.unlink, handle.name)
        return [["sh", handle.name]]

    def test_records_exact_length_from_first_working_command(self):
        cmds = [["false"], *self.script("exec head -c 400000 /dev/zero")]

        async def run():
            async with micsource.MicSource() as source:
                return await source.record(2.0)

        with mock.patch.object(micsource, "get_capture_candidates", return_value=cmds):
            pcm = asyncio.run(run())
        self.assertEqual(len(pcm), RATE * 2 * 2)

    def test_no_source_raises_unavailable(self):
        async def run():
            async with micsource.MicSource():
                return None

        with mock.patch.object(micsource, "get_capture_candidates", return_value=[["false"]]):
            with self.assertRaises(micsource.MicUnavailable):
                asyncio.run(run())
        self.assertFalse(micsource.LOCK.locked())


class FakeSource:
    def __init__(self, pcm: bytes):
        self.pcm = pcm

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_exc):
        return None

    async def record(self, seconds: float) -> bytes:
        return self.pcm[:int(RATE * seconds) * 2]


class MicTestApiTest(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(self.app())

    @staticmethod
    def app() -> FastAPI:
        app = FastAPI()
        app.include_router(ear_api.admin_routes)
        return app

    def test_requires_an_admin_session(self):
        response = self.client.post("/api/ear/mictest", json={"seconds": 5}, headers={"X-Nuxiva-Request": "1"})
        self.assertEqual(response.status_code, 401)

    def test_validates_body_and_returns_both_recordings(self):
        voice = (np.sin(np.arange(RATE * 5) * 0.2) * np.linspace(0.01, 0.2, RATE * 5)).astype(np.float32)
        pcm = np.round(voice * 32767).astype("<i2").tobytes()
        self.app_override()
        with mock.patch.object(mictest_api, "MicSource", lambda: FakeSource(pcm)), \
                mock.patch.object(mictest_api.store, "event"):
            bad = [{"seconds": 60}, {"seconds": 5, "eq": {"enabled": True, "highpass_hz": 900, "low_db": 0, "mid_db": 0,
                                                            "high_db": 0}}, {"seconds": 5, "cmd": "rm"}]
            for body in bad:
                self.assertEqual(self.client.post("/api/ear/mictest", json=body).status_code, 422)
            body = {"seconds": 5, "eq": {"enabled": True, "highpass_hz": 120, "low_db": -3, "mid_db": 2, "high_db": 1}}
            data = self.client.post("/api/ear/mictest", json=body).json()
        self.assertEqual(data["report"]["eq"]["highpass_hz"], 120.0)
        self.assertIn(data["report"]["verdict"], ("ok", "raise", "lower"))
        self.assertTrue(data["audio"]["raw"].startswith("UklGR"))
        self.assertTrue(data["audio"]["processed"].startswith("UklGR"))

    def test_busy_microphone_is_a_conflict(self):
        class Busy(FakeSource):
            async def __aenter__(self):
                raise micsource.MicBusy("mic_busy")

        self.app_override()
        with mock.patch.object(mictest_api, "MicSource", lambda: Busy(b"")):
            response = self.client.post("/api/ear/mictest", json={"seconds": 2})
        self.assertEqual((response.status_code, response.json()["detail"]), (409, "mic_busy"))

    def test_meter_socket_rejects_foreign_origin_and_anonymous(self):
        for headers in ({"origin": "http://evil.example"}, {}):
            with self.assertRaises(WebSocketDisconnect):
                with self.client.websocket_connect("/api/ear/mictest/meter", headers=headers) as socket:
                    socket.receive_json()

    def app_override(self):
        app = self.app()
        app.dependency_overrides[mictest_api.require_admin] = lambda: "admin"
        self.client = TestClient(app)


if __name__ == "__main__":
    unittest.main()
