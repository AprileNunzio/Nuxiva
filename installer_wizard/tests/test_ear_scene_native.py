import sys
import unittest
from pathlib import Path
from unittest import mock

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
for p in (str(ROOT), str(ROOT / "backend"), str(ROOT / "agenti" / "percezione" / "ear")):
    if p not in sys.path:
        sys.path.insert(0, p)

import native_core
from agenti.ear.scene import SoundScene

NATIVE = native_core.load()
READY = NATIVE is not None and hasattr(NATIVE, "RustSoundScene")
RATE = 16000
FRAME = 480


def speech(seconds, gain):
    t = np.arange(int(RATE * seconds)) / RATE
    f0 = 140 + 45 * np.sin(2 * np.pi * 0.9 * t) + 15 * np.sin(2 * np.pi * 3.1 * t)
    phase = np.cumsum(2 * np.pi * f0 / RATE)
    syllable = np.maximum(np.sin(2 * np.pi * 3.5 * t), 0) ** 0.6
    phrase = ((t % 2.2) < 1.7).astype(float)
    voice = sum((np.exp(-((f0 * h - 650) / 350) ** 2) + 0.6 * np.exp(-((f0 * h - 1700) / 450) ** 2)) * np.sin(phase * h)
                for h in range(1, 21))
    return (gain * syllable * phrase * voice).astype(np.float32)


def music(seconds, gain):
    t = np.arange(int(RATE * seconds)) / RATE
    chords = np.array([[261.6, 329.6, 392.0], [220.0, 261.6, 329.6], [174.6, 220.0, 261.6], [196.0, 246.9, 293.7]])
    chord = chords[(t / 0.6).astype(int) % len(chords)]
    tone = sum(np.sin(2 * np.pi * chord[:, n] * h * t) / h for n in range(3) for h in range(1, 7))
    return (gain * (1 + 0.15 * np.sin(2 * np.pi * 2 * t)) * tone).astype(np.float32)


def noise(seconds, gain, seed):
    return (gain * np.random.default_rng(seed).standard_normal(int(RATE * seconds))).astype(np.float32)


def listen(signal, scene=None):
    scene = scene or SoundScene()
    noise_level = 0.004
    out = []
    for start in range(0, len(signal) - FRAME + 1, FRAME):
        frame = signal[start:start + FRAME]
        rms = float(np.sqrt(np.mean(frame * frame)) + 1e-9)
        heard = scene.hear(frame, rms, noise_level, False)
        if not heard.voiced:
            noise_level = noise_level * 0.97 + rms * 0.03
        out.append(heard)
    return out


def share(items):
    return sum(h.voiced for h in items) / max(1, len(items))


@unittest.skipUnless(READY, "modulo nativo ear-core non installato")
class SoundSceneTest(unittest.TestCase):

    def test_engine_is_native(self):
        self.assertTrue(SoundScene().native)

    def test_speech_is_heard_immediately(self):
        heard = listen(speech(8, 0.06) + noise(8, 0.002, 1))
        self.assertTrue(any(h.voiced for h in heard[:6]))
        self.assertFalse(any(h.music for h in heard))
        self.assertGreater(share(heard), 0.3)

    def test_music_alone_no_longer_opens_utterances(self):
        signal = music(12, 0.05)
        native = listen(signal)
        with mock.patch.object(native_core, "symbol", return_value=None):
            fallback = SoundScene()
        python = listen(signal, fallback)
        self.assertLess(share(native[len(native) // 2:]), 0.05)
        self.assertTrue(all(h.music for h in native[len(native) // 2:]))
        self.assertGreater(share(python[len(python) // 2:]), 0.5)

    def test_steady_noise_is_rejected(self):
        heard = listen(noise(4, 0.05, 2))
        self.assertLess(share(heard[20:]), 0.05)
        self.assertTrue(all(h.kind in ("noise", "silence") for h in heard[20:]))

    def test_speech_over_music_and_noise_breaks_through(self):
        bed = music(20, 0.02)
        voice = np.concatenate([np.zeros(RATE * 12, dtype=np.float32), speech(8, 0.09)])
        heard = listen(bed + voice)
        split = RATE * 12 // FRAME
        self.assertLess(share(heard[200:split]), 0.05)
        self.assertGreater(share(heard[split:]), 0.25)
        hiss = noise(9, 0.02, 6)
        voice = np.concatenate([np.zeros(RATE * 3, dtype=np.float32), speech(6, 0.08)])
        heard = listen(hiss + voice)
        self.assertGreater(share(heard[RATE * 3 // FRAME:]), 0.25)

    def test_invalid_frames_are_rejected(self):
        engine = NATIVE.RustSoundScene()
        with self.assertRaises(ValueError):
            engine.feed(b"\x00\x00\x00")
        with self.assertRaises(ValueError):
            engine.feed(np.zeros(20000, dtype="<f4").tobytes())
        voiced, kind, *_ = engine.feed(np.full(480, np.nan, dtype="<f4").tobytes())
        self.assertFalse(voiced)
        self.assertEqual(kind, "silence")
        engine.reset_stream()


class SoundSceneFallbackTest(unittest.TestCase):

    def test_python_rule_without_native_module(self):
        with mock.patch.object(native_core, "symbol", return_value=None):
            scene = SoundScene()
        self.assertFalse(scene.native)
        loud = scene.hear(np.zeros(480, dtype=np.float32), 0.05, 0.004, True)
        quiet = scene.hear(np.zeros(480, dtype=np.float32), 0.005, 0.004, False)
        self.assertTrue(loud.voiced)
        self.assertTrue(loud.music)
        self.assertFalse(quiet.voiced)
        scene.reset()


if __name__ == "__main__":
    unittest.main()
