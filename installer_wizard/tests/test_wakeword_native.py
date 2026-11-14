import math
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
for p in (str(ROOT), str(ROOT / "backend"), str(ROOT / "agenti" / "percezione" / "ear")):
    if p not in sys.path:
        sys.path.insert(0, p)

import native_core
from agenti.ear import wake_template

NATIVE = native_core.load()
READY = NATIVE is not None and hasattr(NATIVE, "wake_enroll")
RATE = 16000

KEY = [(300, 2200, 90), (700, 1200, 140), (400, 1800, 100), (800, 1300, 150), (350, 2300, 120)]
OTHER = [(600, 1000, 160), (300, 800, 100), (700, 1800, 140), (350, 900, 160)]


def word(segments, pitch, tempo, seed):
    rng = np.random.default_rng(seed)
    out, phase, prev = [], 0.0, (segments[0][0], segments[0][1])
    for f1, f2, ms in segments:
        n = int(ms * tempo * RATE / 1000)
        for i in range(n):
            t = i / n
            a, b = prev[0] + (f1 - prev[0]) * t, prev[1] + (f2 - prev[1]) * t
            f0 = pitch * (1 + 0.02 * math.sin(2 * math.pi * 5 * len(out) / RATE))
            phase += 2 * math.pi * f0 / RATE
            s = 0.0
            for h in range(1, 25):
                fh = f0 * h
                if fh > 4000:
                    break
                s += (math.exp(-(((fh - a) / 150) ** 2)) + 0.7 * math.exp(-(((fh - b) / 250) ** 2)) + 0.02) * math.sin(phase * h)
            env = max(math.sqrt(math.sin(t * math.pi)), 0.25)
            out.append(0.12 * env * s + 0.002 * rng.uniform(-1, 1))
        prev = (f1, f2)
    return np.array(out, dtype=np.float32)


def take(pitch, tempo, seed):
    rng = np.random.default_rng(seed + 100)
    pad = np.zeros(int(0.3 * RATE), dtype=np.float32)
    audio = np.concatenate([pad, word(KEY, pitch, tempo, seed), pad]) + 0.003 * rng.uniform(-1, 1, len(pad) * 2 + len(word(KEY, pitch, tempo, seed)))
    return (np.clip(audio, -1, 1) * 32767).astype("<i2").tobytes()


def silence(seconds, amp, seed):
    return np.random.default_rng(seed).uniform(-amp, amp, int(seconds * RATE)).astype(np.float32)


@unittest.skipUnless(READY, "modulo nativo senza il motore della parola di attivazione")
class NativeWakeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.takes = [take(p, t, 10 + i) for i, (p, t) in enumerate([(112, 0.92), (120, 1.0), (128, 1.06), (116, 0.97)])]
        cls.model = wake_template.enroll(cls.takes)

    def run_stream(self, audio, sensitivity=1.0):
        engine = NATIVE.RustWakeword(self.model, sensitivity)
        pcm = (np.clip(audio, -1, 1) * 32767).astype("<i2").tobytes()
        hits = []
        for i in range(0, len(pcm), 2560):
            hits.extend(engine.push(pcm[i:i + 2560]))
        return hits

    def test_enrolled_word_is_detected_once_and_returns_the_audio(self):
        stream = np.concatenate([silence(0.5, 0.003, 1), word(KEY, 122, 1.04, 77), silence(1.0, 0.003, 3)])
        hits = self.run_stream(stream)
        self.assertEqual(len(hits), 1)
        confidence, distance, pcm = hits[0]
        self.assertGreater(confidence, 0.3)
        self.assertGreater(len(pcm), 8000)
        self.assertEqual(len(pcm) % 2, 0)

    def test_other_words_and_loud_noise_never_trigger(self):
        self.assertEqual(self.run_stream(np.concatenate([silence(0.4, 0.003, 4), word(OTHER, 120, 1.0, 5), silence(0.8, 0.003, 6)])), [])
        self.assertEqual(self.run_stream(silence(4.0, 0.6, 7)), [])

    def test_model_bytes_are_integrity_checked(self):
        tampered = bytearray(self.model)
        tampered[40] ^= 1
        with self.assertRaises(ValueError):
            NATIVE.RustWakeword(bytes(tampered))
        with self.assertRaises(ValueError):
            NATIVE.RustWakeword(b"")
        with self.assertRaises(ValueError):
            NATIVE.RustWakeword(self.model, float("nan"))

    def test_enrollment_rejects_bad_recordings(self):
        with self.assertRaises(ValueError):
            wake_template.enroll(self.takes[:2])
        with self.assertRaises(ValueError):
            wake_template.enroll([self.takes[0], self.takes[1], b"\x00" * 32000])
        with self.assertRaises(ValueError):
            wake_template.enroll([b"x"] * 11)
        with self.assertRaises(ValueError):
            wake_template.enroll(["text"] * 3)

    def test_audio_packets_are_validated(self):
        engine = NATIVE.RustWakeword(self.model)
        with self.assertRaises(ValueError):
            engine.push(b"\x00")
        with self.assertRaises(ValueError):
            engine.push(b"\x00" * (16000 * 2 * 31))

    def test_decision_table_matches_the_policy(self):
        decide = NATIVE.wake_decide
        self.assertEqual(decide(0.8, "authorized", 0.7, True, 0.3)[:2], (True, "accept"))
        self.assertEqual(decide(0.8, "unknown", 0.1, True, 0.3)[:2], (False, "reject_speaker"))
        self.assertEqual(decide(0.8, "ambiguous", 0.0, True, 0.3)[:2], (False, "reject_ambiguous"))
        self.assertEqual(decide(0.8, "unavailable", 0.0, True, 0.3)[:2], (False, "needs_enrollment"))
        self.assertEqual(decide(0.8, "unavailable", 0.0, False, 0.3)[:2], (True, "accept"))
        self.assertEqual(decide(0.1, "authorized", 0.9, True, 0.3)[:2], (False, "reject_wake"))
        with self.assertRaises(ValueError):
            decide(0.8, "root", 0.0, True, 0.3)


@unittest.skipUnless(READY, "modulo nativo senza il motore della parola di attivazione")
class TemplateServiceTest(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp())
        self.takes = [take(p, t, 10 + i) for i, (p, t) in enumerate([(112, 0.92), (120, 1.0), (128, 1.06)])]
        self.path = wake_template.model_path(self.dir, "ehi_nuxiva")
        wake_template.save(self.path, wake_template.enroll(self.takes))

    def test_saved_model_loads_and_detects_from_float_frames(self):
        engine = wake_template.TemplateWake.load(self.path)
        self.assertIsNotNone(engine)
        stream = np.concatenate([silence(0.5, 0.003, 1), word(KEY, 122, 1.04, 77), silence(1.0, 0.003, 3)])
        hit = False
        for i in range(0, len(stream), 1280):
            hit = engine.feed(stream[i:i + 1280]) or hit
        self.assertTrue(hit)
        self.assertGreater(engine.pcm.size, 8000)
        self.assertEqual(oct(self.path.stat().st_mode & 0o777), oct(0o644))

    def test_corrupt_model_file_is_ignored_not_trusted(self):
        raw = bytearray(self.path.read_bytes())
        raw[50] ^= 0xFF
        self.path.write_bytes(bytes(raw))
        self.assertIsNone(wake_template.TemplateWake.load(self.path))
        self.assertIsNone(wake_template.TemplateWake.load(self.dir / "assente.nxwk"))

    def test_save_refuses_data_the_engine_cannot_parse(self):
        with self.assertRaises(ValueError):
            wake_template.save(self.dir / "x.nxwk", b"garbage")
        self.assertFalse((self.dir / "x.nxwk").exists())

    def test_speaker_gate_rejects_a_known_other_voice_only_when_enforced(self):
        engine = wake_template.TemplateWake.load(self.path)
        engine.score, engine.pcm = 0.8, np.zeros(20000, dtype=np.float32)
        stranger = SimpleNamespace(ready=True, samples={"a": 1}, embed=lambda audio: np.ones(4, dtype=np.float32),
                                   verdict=lambda probe: {"slug": None, "ambiguous": False, "score": 0.1})
        owner = SimpleNamespace(ready=True, samples={"a": 1}, embed=lambda audio: np.ones(4, dtype=np.float32),
                                verdict=lambda probe: {"slug": "a", "ambiguous": False, "score": 0.9})
        short = SimpleNamespace(ready=True, samples={"a": 1}, embed=lambda audio: None, verdict=lambda probe: {})
        self.assertEqual(wake_template.judge(engine, stranger, True), (False, "reject_speaker"))
        self.assertEqual(wake_template.judge(engine, stranger, False)[0], True)
        self.assertTrue(wake_template.judge(engine, owner, True)[0])
        self.assertTrue(wake_template.judge(engine, short, True)[0])
        engine.score = 0.1
        self.assertEqual(wake_template.judge(engine, owner, True), (False, "reject_wake"))

    def test_candidates_follow_the_assistant_name(self):
        self.assertEqual(wake_template.candidates("Ada"), ["ehi_ada", "ada"])
        self.assertEqual(wake_template.candidates("", ""), ["ehi_nuxiva"])
        self.assertEqual(wake_template.candidates("../x"), [])


class WithoutNativeTest(unittest.TestCase):
    def test_enrollment_reports_an_unavailable_engine_instead_of_pretending(self):
        with mock.patch.object(wake_template.native_core, "symbol", return_value=None):
            self.assertFalse(wake_template.available())
            with self.assertRaises(RuntimeError):
                wake_template.enroll([b"\x00\x00"] * 3)
            self.assertIsNone(wake_template.TemplateWake.load(Path("/nonexistent.nxwk")))


if __name__ == "__main__":
    unittest.main()
