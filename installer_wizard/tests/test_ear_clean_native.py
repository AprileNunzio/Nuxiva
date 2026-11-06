import os
import sys
import unittest
from pathlib import Path
from unittest import mock

import numpy as np

EAR = Path(__file__).resolve().parents[1] / "features" / "ear"
for p in (str(Path(__file__).resolve().parents[1]), str(Path(__file__).resolve().parents[1] / "backend"), str(EAR)):
    if p not in sys.path:
        sys.path.insert(0, p)

import native_core
from features.ear import conditioner
from features.ear.conditioner import HOP, NativeConditioner, RustConditioner

import enhance
import levels
from tuning import tuning

NATIVE = native_core.load()
READY = NATIVE is not None and all(hasattr(NATIVE, n) for n in ("RustDenoiser", "RustNoiseTracker", "ear_clean_utterance",
                                                                "ear_normalize", "ear_utterance_gain"))
RATE = 16000
CHUNK = 960


def run(engine, signal):
    pcm = (np.clip(signal, -1.0, 32767 / 32768) * 32768).astype("<i2").tobytes()
    out = b"".join(engine.process(pcm[i:i + CHUNK]) for i in range(0, len(pcm), CHUNK))
    return np.frombuffer(out, dtype="<i2").astype(np.float32) / 32768.0


def rms(x):
    return float(np.sqrt(np.mean(x * x)))


def speech_like(seconds):
    t = np.arange(int(RATE * seconds)) / RATE
    f0 = 150 + 40 * np.sin(2 * np.pi * 0.7 * t)
    phase = np.cumsum(2 * np.pi * f0 / RATE)
    syllable = np.maximum(np.sin(2 * np.pi * 4 * t), 0) ** 0.6
    voice = np.zeros_like(t)
    for h in range(1, 21):
        hf = f0 * h
        formant = np.exp(-((hf - 700) / 400) ** 2) + 0.6 * np.exp(-((hf - 1800) / 500) ** 2)
        voice += formant * np.sin(phase * h)
    return (0.08 * syllable * voice).astype(np.float32)


def snr(clean, test):
    return 10 * np.log10(np.sum(clean.astype(np.float64) ** 2) / max(np.sum((clean - test).astype(np.float64) ** 2), 1e-20))


@unittest.skipUnless(READY, "modulo nativo ear-core non installato")
class RustConditionerTest(unittest.TestCase):

    def setUp(self):
        self.rng = np.random.default_rng(29)
        self.t = np.arange(RATE * 4) / RATE

    def test_build_uses_rust(self):
        self.assertIsInstance(conditioner.build(), RustConditioner)

    def test_bypass_returns_identical_pcm(self):
        engine = conditioner.build(highpass_hz=0, suppress=False)
        pcm = (self.rng.standard_normal(480) * 3000).astype("<i2").tobytes()
        self.assertEqual(engine.process(pcm), pcm)
        self.assertFalse(engine.enabled)

    def test_rejects_malformed_packets(self):
        engine = conditioner.build()
        with self.assertRaises(ValueError):
            engine.process(b"\x00")
        with self.assertRaises(ValueError):
            engine.process("pcm")
        self.assertEqual(engine.process(b""), b"")

    def test_reconstruction_is_transparent_in_voice_band(self):
        tone = 0.3 * np.sin(2 * np.pi * 440 * self.t)
        out = run(conditioner.build(highpass_hz=90, suppress=False), tone)
        self.assertGreater(len(out), len(tone) - 2 * HOP)
        self.assertLess(float(np.max(np.abs(out[HOP:] - tone[HOP:len(out)]))), 0.01)

    def test_dc_offset_and_mains_hum_are_removed(self):
        self.assertLess(rms(run(conditioner.build(suppress=False), np.full(len(self.t), 0.08))[RATE:]), 0.002)
        hum = 0.08 + 0.05 * np.sin(2 * np.pi * 50 * self.t)
        self.assertLess(rms(run(conditioner.build(), hum)[RATE:]), 0.005)

    def test_stationary_noise_is_attenuated_and_speech_band_kept(self):
        noise = 0.02 * self.rng.standard_normal(len(self.t))
        signal = noise.copy()
        burst = slice(2 * RATE, int(2.5 * RATE))
        signal[burst] += 0.1 * np.sin(2 * np.pi * 500 * self.t[burst])
        out = run(conditioner.build(), signal)
        self.assertLess(rms(out[3 * RATE:]), rms(noise[3 * RATE:]) * 0.3)
        self.assertGreater(rms(out[2 * RATE + 300:int(2.5 * RATE) - 300]), 0.1 / np.sqrt(2) * 0.85)

    def test_restart_drops_stream_state(self):
        engine = conditioner.build()
        run(engine, 0.01 * self.rng.standard_normal(RATE))
        noise = engine.engine.noise()
        engine.process(b"\x01\x00" * 100)
        engine.restart()
        self.assertEqual(engine.engine.pending(), 0)
        self.assertEqual(engine.engine.noise(), noise)

    def test_output_saturates_without_wrapping(self):
        out = run(conditioner.build(highpass_hz=0, suppress=False, floor=1.0), np.full(RATE, 0.999))
        self.assertTrue(np.all(out[HOP:] > 0.9))

    def test_environment_configuration_is_bounded(self):
        with mock.patch.dict(os.environ, {"NUXIVA_EAR_HOST_NS": "0", "NUXIVA_EAR_HOST_HIGHPASS_HZ": "9999",
                                          "NUXIVA_EAR_HOST_NS_FLOOR": "-3"}):
            engine = conditioner.from_env()
        self.assertFalse(engine.suppress)
        self.assertAlmostEqual(engine.floor, 0.05, places=5)
        self.assertTrue(engine.enabled)
        self.assertEqual(engine.engine.highpass_hz, 300.0)
        with mock.patch.dict(os.environ, {"NUXIVA_EAR_HOST_NS": "0", "NUXIVA_EAR_HOST_HIGHPASS_HZ": "0"}):
            self.assertFalse(conditioner.from_env().enabled)

    def test_rust_cleans_noisy_speech_better_than_python(self):
        clean = speech_like(5)
        for level in (0.06, 0.1):
            noisy = (clean + level * self.rng.standard_normal(len(clean))).astype(np.float32)
            rust = run(conditioner.build(), noisy)
            python = run(NativeConditioner(), noisy)
            region = slice(RATE, 4 * RATE)
            with self.subTest(level=level):
                self.assertGreater(snr(clean[region], rust[region]), snr(clean[region], noisy[region]) + 3.0)
                self.assertGreater(snr(clean[region], rust[region]), snr(clean[region], python[region]))


@unittest.skipUnless(READY, "modulo nativo ear-core non installato")
class RustUtteranceTest(unittest.TestCase):

    def setUp(self):
        self.rng = np.random.default_rng(5)

    def profile(self, level):
        profile = enhance.NoiseProfile()
        self.assertIsNotNone(profile.native)
        noise = (level * self.rng.standard_normal(RATE)).astype(np.float32)
        for start in range(0, len(noise), 480):
            profile.learn(noise[start:start + 480])
        self.assertIsNotNone(profile.psd())
        return profile

    def test_suppression_beats_the_python_engine(self):
        clean = speech_like(5)
        for level in (0.025, 0.06, 0.1):
            profile = self.profile(level)
            noisy = (clean + level * self.rng.standard_normal(len(clean))).astype(np.float32)
            rust = enhance.suppress(noisy, profile)
            python = enhance.denoise(enhance.highpass(noisy), profile.magnitude)
            region = slice(RATE, 5 * RATE)
            self.assertEqual(len(rust), len(noisy))
            with self.subTest(level=level):
                self.assertGreater(snr(clean[region], rust[region]), snr(clean[region], noisy[region]))
                self.assertGreater(snr(clean[region], rust[region]), snr(clean[region], python[region]))

    def test_clean_keeps_length_and_bounds(self):
        profile = self.profile(0.02)
        noisy = (speech_like(2) * 6 + 0.02 * self.rng.standard_normal(2 * RATE)).astype(np.float32)
        with mock.patch.dict(os.environ, {"NUXIVA_EAR_ENHANCE_ENGINE": "spectral"}):
            out = enhance.clean(noisy, profile)
        self.assertEqual(len(out), len(noisy))
        self.assertTrue(np.all(np.abs(out) <= 0.97 + 1e-6))

    def test_normalize_matches_python(self):
        signals = [np.ones(1000, dtype=np.float32) * 2.5, np.zeros(640, dtype=np.float32),
                   (0.003 * self.rng.standard_normal(8000)).astype(np.float32), speech_like(1.3),
                   np.repeat(np.arange(1, 11, dtype=np.float32) * 0.001, 320), np.float32([0.2, -0.1, 0.05])]
        target = enhance._env_f("NUXIVA_EAR_TARGET_RMS", enhance.TARGET_RMS, 0.03, 0.2)
        for signal in signals:
            with self.subTest(size=len(signal)):
                np.testing.assert_allclose(enhance.normalize(signal), enhance._py_normalize(signal, target), atol=2e-4)
                self.assertAlmostEqual(NATIVE.ear_utterance_gain(signal.astype("<f4").tobytes(), target, tuning.max_gain()),
                                       levels.utterance_gain(signal, target, tuning.max_gain()), places=3)

    def test_invalid_inputs_are_rejected(self):
        with self.assertRaises(ValueError):
            NATIVE.ear_clean_utterance(b"\x00\x00\x00")
        with self.assertRaises(ValueError):
            NATIVE.ear_normalize(b"", 0.0, 18.0)
        self.assertEqual(NATIVE.ear_clean_utterance(b""), b"")
        nan = np.full(1024, np.nan, dtype="<f4").tobytes()
        self.assertTrue(np.all(np.isfinite(np.frombuffer(NATIVE.ear_clean_utterance(nan), dtype="<f4"))))


class FallbackTest(unittest.TestCase):

    def test_python_engines_answer_without_the_native_module(self):
        with mock.patch.object(native_core, "symbol", return_value=None):
            engine = conditioner.build()
            self.assertIsInstance(engine, NativeConditioner)
            profile = enhance.NoiseProfile()
            self.assertIsNone(profile.native)
            signal = (0.05 * np.random.default_rng(1).standard_normal(8000)).astype(np.float32)
            profile.learn(signal)
            self.assertEqual(len(enhance.clean(signal, profile)), len(signal))


if __name__ == "__main__":
    unittest.main()
