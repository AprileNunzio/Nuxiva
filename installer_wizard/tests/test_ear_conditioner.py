import unittest
from unittest.mock import patch

import numpy as np

from features.ear.conditioner import HOP, NativeConditioner

RATE = 16000
CHUNK = 960


def run(conditioner, signal):
    pcm = (np.clip(signal, -1.0, 32767 / 32768) * 32768).astype("<i2").tobytes()
    out = b"".join(conditioner.process(pcm[i:i + CHUNK]) for i in range(0, len(pcm), CHUNK))
    return np.frombuffer(out, dtype="<i2").astype(np.float32) / 32768.0


def rms(x):
    return float(np.sqrt(np.mean(x * x)))


class NativeConditionerTest(unittest.TestCase):
    def setUp(self):
        self.rng = np.random.default_rng(29)
        self.t = np.arange(RATE * 4) / RATE

    def test_bypass_returns_identical_pcm(self):
        conditioner = NativeConditioner(highpass_hz=0, suppress=False)
        pcm = (self.rng.standard_normal(480) * 3000).astype("<i2").tobytes()
        self.assertEqual(conditioner.process(pcm), pcm)

    def test_rejects_malformed_packets(self):
        conditioner = NativeConditioner()
        with self.assertRaises(ValueError):
            conditioner.process(b"\x00")
        with self.assertRaises(ValueError):
            conditioner.process("pcm")
        self.assertEqual(conditioner.process(b""), b"")

    def test_reconstruction_is_transparent_in_voice_band(self):
        tone = 0.3 * np.sin(2 * np.pi * 440 * self.t)
        out = run(NativeConditioner(highpass_hz=90, suppress=False), tone)
        self.assertGreater(len(out), len(tone) - 2 * HOP)
        self.assertLess(float(np.max(np.abs(out[HOP:] - tone[HOP:len(out)]))), 0.01)

    def test_dc_offset_is_removed_by_highpass(self):
        out = run(NativeConditioner(suppress=False), np.full(len(self.t), 0.08))
        self.assertLess(rms(out[RATE:]), 0.002)

    def test_dc_offset_and_mains_hum_are_removed(self):
        hum = 0.08 + 0.05 * np.sin(2 * np.pi * 50 * self.t)
        out = run(NativeConditioner(), hum)
        self.assertLess(rms(out[RATE:]), 0.005)

    def test_stationary_noise_is_attenuated_and_speech_band_kept(self):
        noise = 0.02 * self.rng.standard_normal(len(self.t))
        signal = noise.copy()
        burst = slice(2 * RATE, int(2.5 * RATE))
        signal[burst] += 0.1 * np.sin(2 * np.pi * 500 * self.t[burst])
        out = run(NativeConditioner(), signal)
        self.assertLess(rms(out[3 * RATE:]), rms(noise[3 * RATE:]) * 0.6)
        kept = rms(out[2 * RATE + 300:int(2.5 * RATE) - 300])
        self.assertGreater(kept, 0.1 / np.sqrt(2) * 0.9)

    def test_restart_keeps_noise_profile_but_drops_stream_state(self):
        conditioner = NativeConditioner()
        run(conditioner, 0.01 * self.rng.standard_normal(RATE))
        profile = conditioner.noise.copy()
        conditioner.process(b"\x01\x00" * 100)
        conditioner.restart()
        self.assertEqual(len(conditioner.pending), 0)
        self.assertFalse(conditioner.overlap.any())
        np.testing.assert_array_equal(conditioner.noise, profile)

    def test_output_saturates_without_wrapping(self):
        out = run(NativeConditioner(highpass_hz=0, suppress=False, floor=1.0), np.full(RATE, 0.999))
        self.assertTrue(np.all(out[HOP:] > 0.9))

    def test_environment_configuration_is_bounded(self):
        with patch.dict("os.environ", {"NUXIVA_EAR_HOST_NS": "0", "NUXIVA_EAR_HOST_HIGHPASS_HZ": "9999",
                                       "NUXIVA_EAR_HOST_NS_FLOOR": "-3"}):
            conditioner = NativeConditioner.from_env()
        self.assertFalse(conditioner.suppress)
        self.assertEqual(conditioner.floor, 0.05)
        self.assertTrue(conditioner.enabled)
        with patch.dict("os.environ", {"NUXIVA_EAR_HOST_NS": "0", "NUXIVA_EAR_HOST_HIGHPASS_HZ": "0"}):
            self.assertFalse(NativeConditioner.from_env().enabled)


if __name__ == "__main__":
    unittest.main()
