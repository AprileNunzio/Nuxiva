import tempfile
import unittest
from pathlib import Path

from features.nvr.vault import MediaVault


class TestNvrMediaVault(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.vault = MediaVault(continuous_seconds=2, event_seconds=10)
        self.vault.root = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_encrypt_and_decrypt_roundtrip(self):
        cam_id = "test_cam_01"
        fake_raw = Path(self.temp_dir.name) / "seg_20261110_120000.mp4"
        payload = b"FAKE_AUDIO_VIDEO_PAYLOAD_CHUNK_DATA_" * 500
        fake_raw.write_bytes(payload)

        enc_path = self.vault.encrypt_file(cam_id, fake_raw, tier="continuous")
        self.assertTrue(enc_path.exists())
        self.assertFalse(fake_raw.exists())

        decrypted = self.vault.decrypt_file(cam_id, enc_path)
        self.assertEqual(decrypted, payload)

    def test_streaming_chunks(self):
        cam_id = "test_cam_stream"
        fake_raw = Path(self.temp_dir.name) / "seg_20261110_120500.mp4"
        payload = b"STREAMING_TEST_BYTES_" * 1000
        fake_raw.write_bytes(payload)

        enc_path = self.vault.encrypt_file(cam_id, fake_raw, tier="continuous")
        chunks = list(self.vault.stream_chunks(cam_id, enc_path))
        self.assertGreater(len(chunks), 0)
        self.assertEqual(b"".join(chunks), payload)

    def test_pruning_expiration(self):
        cam_id = "test_cam_prune"
        fake_raw = Path(self.temp_dir.name) / "seg_20261110_121000.mp4"
        fake_raw.write_bytes(b"DATA")

        enc_path = self.vault.encrypt_file(cam_id, fake_raw, tier="continuous")
        self.assertTrue(enc_path.exists())

        self.assertFalse(self.vault.is_expired("continuous", 1000, 1001))
        self.assertTrue(self.vault.is_expired("continuous", 1000, 1005))
        self.assertFalse(self.vault.is_expired("pinned", 1000, 999999))


if __name__ == "__main__":
    unittest.main()
