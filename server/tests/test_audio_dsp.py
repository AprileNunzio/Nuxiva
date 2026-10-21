import math
import unittest

from server.core.audio_dsp import (
    AudioCleanerBridge,
    AudioDevice,
    FailoverDeviceRouterBridge,
    MediaPlaybackState,
    MultiMicTriageBridge,
    SatelliteAudioReport,
)


class TestAudioDsp(unittest.TestCase):
    def test_media_playback_state_roundtrip(self) -> None:
        state = MediaPlaybackState(
            is_active=True,
            source_id="stream.iptv.living_room",
            stream_type="IPTV_LIVE",
            volume_normalized=0.75,
            reference_energy=0.04,
        )
        d = state.to_dict()
        restored = MediaPlaybackState.from_dict(d)
        self.assertTrue(restored.is_active)
        self.assertEqual(restored.source_id, "stream.iptv.living_room")
        self.assertEqual(restored.stream_type, "IPTV_LIVE")
        self.assertAlmostEqual(restored.volume_normalized, 0.75)

    def test_cleaner_silence_gated(self) -> None:
        cleaner = AudioCleanerBridge()
        silence_bytes = bytes(640)
        media_idle = MediaPlaybackState()
        res = cleaner.process_pcm(silence_bytes, media_idle)

        self.assertTrue(res["is_gated"])
        self.assertFalse(res["vad"]["is_speech"])
        self.assertEqual(res["attenuation_applied"], 0.0)

    def test_cleaner_speech_detection(self) -> None:
        cleaner = AudioCleanerBridge()
        samples = []
        for i in range(320):
            t = i / 16000.0
            val = math.sin(2.0 * math.pi * 1000.0 * t) * 12000.0
            clamped = max(-32768, min(32767, int(val)))
            samples.append(clamped)

        pcm_bytes = b"".join(s.to_bytes(2, byteorder="little", signed=True) for s in samples)
        media_idle = MediaPlaybackState()
        res = cleaner.process_pcm(pcm_bytes, media_idle)

        self.assertFalse(res["is_gated"])
        self.assertTrue(res["vad"]["is_speech"])

    def test_failover_device_routing(self) -> None:
        router = FailoverDeviceRouterBridge(is_proximity=False)
        bt = AudioDevice("bt_earbuds", "device.bluetooth.buds", priority=1, is_connected=True, is_bluetooth=True)
        builtin = AudioDevice("builtin_mic", "device.builtin.array", priority=2, is_connected=True, is_bluetooth=False)

        router.register_device(bt)
        router.register_device(builtin)

        active = router.resolve_active_device()
        self.assertIsNotNone(active)
        self.assertEqual(active.id, "bt_earbuds")

        router.update_connection_state("bt_earbuds", is_connected=False)
        fallback = router.resolve_active_device()
        self.assertIsNotNone(fallback)
        self.assertEqual(fallback.id, "builtin_mic")

    def test_multi_mic_proximity_triage(self) -> None:
        triage = MultiMicTriageBridge(hysteresis_margin=2.0)
        near = SatelliteAudioReport("desk_satellite", timestamp_ms=1000, snr_db=28.0, energy_rms=0.06, speech_confidence=0.95)
        far = SatelliteAudioReport("kitchen_satellite", timestamp_ms=1000, snr_db=9.0, energy_rms=0.01, speech_confidence=0.30)

        winner = triage.elect_best_source([near, far])
        self.assertEqual(winner, "desk_satellite")


if __name__ == "__main__":
    unittest.main()
