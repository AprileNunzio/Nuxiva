import unittest
import numpy as np
import base64
import time
from server.features.multimodal_surveillance.interfaces import (
    AudioChunkPayload,
    VideoFramePayload,
    SatelliteNodeConfig,
    SemanticSearchQuery,
)
from server.features.multimodal_surveillance.audio_enhancer import audio_enhancer
from server.features.multimodal_surveillance.audio_continuous_recorder import audio_continuous_recorder
from server.features.multimodal_surveillance.video_continuous_recorder import video_continuous_recorder
from server.features.multimodal_surveillance.node_device_registry import node_device_registry
from server.features.multimodal_surveillance.encryption_vault import vault

class MultimodalSurveillanceTest(unittest.TestCase):
    def test_audio_enhancer_amplification_and_denoising(self):
        t = np.linspace(0, 1.0, 16000, endpoint=False)
        clean_sine = 0.1 * np.sin(2 * np.pi * 440 * t)
        noise = 0.02 * np.random.normal(size=16000)
        signal = clean_sine + noise

        enhanced, orig_rms, new_rms, snr_gain, features = audio_enhancer.enhance(signal)
        self.assertGreater(new_rms, orig_rms)
        self.assertGreater(snr_gain, 0.0)
        self.assertIn("zero_crossing_rate", features)
        self.assertIn("clarity_score", features)

    def test_audio_continuous_recorder_ingest(self):
        dummy_pcm = (np.sin(np.linspace(0, 10, 8000)) * 10000).astype(np.int16).tobytes()
        b64_audio = base64.b64encode(dummy_pcm).decode("ascii")

        payload = AudioChunkPayload(
            node_id="test_node_sat_01",
            microphone_id="mic_gate_front",
            timestamp=time.time(),
            sample_rate=16000,
            audio_base64=b64_audio
        )
        result = audio_continuous_recorder.ingest_audio_chunk(payload)
        self.assertEqual(result.node_id, "test_node_sat_01")
        self.assertGreater(result.enhanced_rms, 0.0)
        latest = audio_continuous_recorder.get_latest_segments("test_node_sat_01")
        self.assertGreaterEqual(len(latest), 1)

    def test_video_continuous_recorder_and_courier_detection(self):
        frame_payload = VideoFramePayload(
            node_id="master_server",
            camera_id="cam_main_entrance",
            timestamp=time.time(),
            frame_base64="ZHVtbXlfZnJhbWVfYmFzZTY0X3N0cmluZ19kYXRhXzIwMjY="
        )
        entry = video_continuous_recorder.ingest_frame(frame_payload)
        self.assertEqual(entry.camera_id, "cam_main_entrance")
        self.assertIsNotNone(entry.courier_details)
        self.assertIsNotNone(entry.person_details)
        self.assertIn("vestiti", entry.detailed_description)

        search = SemanticSearchQuery(query="A che ora è venuto il corriere?")
        resp = video_continuous_recorder.query_semantic_logs(search)
        self.assertGreaterEqual(resp.total_found, 1)
        self.assertIn("corriere", resp.direct_answer.lower())
        self.assertIn("arrivato", resp.direct_answer.lower())

    def test_node_auto_configuration(self):
        configured = node_device_registry.auto_configure_satellite(
            node_id="satellite_garage",
            name="Satellite Garage & Parcheggio",
            endpoint_url="http://192.168.1.155:9000",
            detected_camera="cam_garage_thermal",
            detected_mic="mic_garage_ceiling",
            detected_audio_out="spk_garage_alert",
            psk="psk_garage_secret_key_2026_secured"
        )
        self.assertEqual(configured.node_id, "satellite_garage")
        self.assertEqual(configured.default_camera_id, "cam_garage_thermal")
        self.assertEqual(configured.default_microphone_id, "mic_garage_ceiling")
        self.assertEqual(configured.default_audio_output_id, "spk_garage_alert")

        found = node_device_registry.get_node("satellite_garage")
        self.assertIsNotNone(found)
        self.assertEqual(found.name, "Satellite Garage & Parcheggio")

    def test_zero_trust_encryption_vault(self):
        secret_log = "Dettagli sensibili sorveglianza: individuo identificato con targa AA000BB"
        encrypted_token = vault.encrypt_string(secret_log)
        self.assertNotEqual(secret_log, encrypted_token)

        decrypted = vault.decrypt_string(encrypted_token)
        self.assertEqual(secret_log, decrypted)

if __name__ == "__main__":
    unittest.main()
