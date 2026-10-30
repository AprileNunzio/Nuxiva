import base64
import importlib.util
import random
import unittest
from unittest import mock

import numpy as np

from server.core.audio_dsp import AudioCleanerBridge, MediaPlaybackState
from server.core.core_platform import aead
from server.core.core_platform.errors import CortexFailure
from server.features.human_affective_engine.vocal_biomarker_extractor import VocalBiomarkerAnalyzer
from server.features.multimodal_surveillance.audio_enhancer import AudioSignalEnhancer
from server.features.multimodal_surveillance.encryption_vault import ZeroTrustEncryptionVault
from server.features.wearable_vitals_hub import protocol_parser as parser_module

NATIVE = importlib.util.find_spec("nuxiva_native") is not None
SECRET = "f3a9c1d7e5b2084f6a1c3e5d7b9f0a2c4e6b8d0f1a3c5e7"


def tone(freq: float, count: int = 16000, amplitude: float = 0.4, rate: int = 16000) -> np.ndarray:
    t = np.arange(count, dtype=np.float64) / rate
    return (np.sin(2 * np.pi * freq * t) * amplitude).astype(np.float32)


def pcm16(signal: np.ndarray) -> bytes:
    return (np.clip(signal, -1, 1) * 32767).astype("<i2").tobytes()


class AudioCleanerBinaryTest(unittest.TestCase):
    def test_pcm_clean_is_bytes_with_frame_length(self) -> None:
        frame = pcm16(tone(1000.0, 320, 0.4))
        res = AudioCleanerBridge().process_pcm(frame, MediaPlaybackState())
        self.assertIsInstance(res["pcm_clean"], bytes)
        self.assertEqual(len(res["pcm_clean"]), len(frame))
        self.assertEqual(res["frame_samples"], 320)

    def test_fallback_pcm_clean_is_bytes(self) -> None:
        bridge = AudioCleanerBridge()
        bridge._native = None
        res = bridge.process_pcm(bytes(641), MediaPlaybackState())
        self.assertEqual(res["pcm_clean"], bytes(640))
        self.assertTrue(res["is_gated"])

    @unittest.skipUnless(NATIVE, "nuxiva_native not installed")
    def test_native_rejects_oversized_frame(self) -> None:
        with self.assertRaises(ValueError):
            AudioCleanerBridge().process_pcm(bytes(2 * 1024 * 1024), MediaPlaybackState())


class SignalEnhancerParityTest(unittest.TestCase):
    def test_process_matches_numpy_reference(self) -> None:
        signal = tone(440.0, 4000, 0.05)
        b64 = base64.b64encode(pcm16(signal)).decode("ascii")
        fast = AudioSignalEnhancer().process_pcm16_base64(b64)
        reference = AudioSignalEnhancer()
        reference._native = None
        slow = reference.process_pcm16_base64(b64)
        self.assertEqual(fast.sample_count, slow.sample_count)
        self.assertAlmostEqual(fast.original_rms, slow.original_rms, places=4)
        self.assertAlmostEqual(fast.enhanced_rms, slow.enhanced_rms, places=3)
        self.assertAlmostEqual(fast.snr_gain_db, slow.snr_gain_db, places=2)
        for key in ("zero_crossing_rate", "crest_factor", "clarity_score"):
            self.assertAlmostEqual(fast.features[key], slow.features[key], places=3)

    def test_invalid_base64_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            AudioSignalEnhancer().process_pcm16_base64("@@not-base64@@")


class VoiceBiomarkerParityTest(unittest.TestCase):
    def test_pitch_matches_reference(self) -> None:
        signal = tone(200.0, 16000, 0.3)
        fast = VocalBiomarkerAnalyzer().extract_biomarkers(signal)
        reference = VocalBiomarkerAnalyzer()
        reference._native = None
        slow = reference.extract_biomarkers(signal)
        self.assertAlmostEqual(fast.pitch_f0_mean_hz, slow.pitch_f0_mean_hz, delta=1.0)
        self.assertAlmostEqual(fast.speech_pause_ratio, slow.speech_pause_ratio, places=6)
        self.assertAlmostEqual(fast.vocal_energy_rms, slow.vocal_energy_rms, places=4)
        self.assertAlmostEqual(fast.monotone_score, slow.monotone_score, places=3)


class BleHeartRateParityTest(unittest.TestCase):
    def test_native_and_python_agree_on_random_frames(self) -> None:
        rng = random.Random(1337)
        parser = parser_module.UniversalProtocolParser()
        for _ in range(500):
            frame = bytes(rng.randrange(256) for _ in range(rng.randrange(0, 24)))
            fast = parser.parse_ble_heart_rate_frame("dev", frame)
            with mock.patch.object(parser_module, "NATIVE_BLE", None):
                slow = parser.parse_ble_heart_rate_frame("dev", frame)
            self.assertEqual(fast.heart_rate_bpm, slow.heart_rate_bpm, frame.hex())
            if slow.hrv_rmssd_ms is None:
                self.assertIsNone(fast.hrv_rmssd_ms, frame.hex())
            else:
                self.assertAlmostEqual(fast.hrv_rmssd_ms, slow.hrv_rmssd_ms, places=9, msg=frame.hex())

    def test_oversized_frame_is_ignored(self) -> None:
        result = parser_module.protocol_parser.parse_ble_heart_rate_frame("dev", bytes([0x00, 72]) * 512)
        self.assertIsNone(result.heart_rate_bpm)


class SurveillanceVaultTest(unittest.TestCase):
    def test_roundtrip_and_tamper_detection(self) -> None:
        vault = ZeroTrustEncryptionVault(SECRET)
        token = vault.encrypt_string("targa AA000BB")
        self.assertEqual(vault.decrypt_string(token), "targa AA000BB")
        raw = bytearray(base64.b64decode(token))
        raw[-1] ^= 0x01
        with self.assertRaises(CortexFailure):
            vault.decrypt_string(base64.b64encode(bytes(raw)).decode("ascii"))

    def test_nonces_are_unique(self) -> None:
        vault = ZeroTrustEncryptionVault(SECRET)
        nonces = {vault.encrypt_bytes(b"x")[0] for _ in range(64)}
        self.assertEqual(len(nonces), 64)

    def test_weak_or_placeholder_secret_is_refused(self) -> None:
        for secret in ("short", "0" * 64):
            with self.assertRaises(CortexFailure):
                ZeroTrustEncryptionVault(secret)

    def test_foreign_key_cannot_decrypt(self) -> None:
        token = ZeroTrustEncryptionVault(SECRET).encrypt_string("segreto")
        with self.assertRaises(CortexFailure):
            ZeroTrustEncryptionVault(SECRET[::-1]).decrypt_string(token)

    @unittest.skipUnless(NATIVE, "nuxiva_native not installed")
    def test_native_and_software_aead_interoperate(self) -> None:
        native_key = aead.derive_key(SECRET.encode(), b"ctx").unwrap()
        sealed = aead.seal(native_key, b"aad", b"payload").unwrap()
        with mock.patch.object(aead, "_native_ready", return_value=False):
            software_key = aead.derive_key(SECRET.encode(), b"ctx").unwrap()
            self.assertEqual(native_key, software_key)
            self.assertEqual(aead.open_sealed(software_key, b"aad", sealed).unwrap(), b"payload")
            resealed = aead.seal(software_key, b"aad", b"back").unwrap()
        self.assertEqual(aead.open_sealed(native_key, b"aad", resealed).unwrap(), b"back")


if __name__ == "__main__":
    unittest.main()
