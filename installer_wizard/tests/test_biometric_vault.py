import os
import stat
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import numpy as np

from features.biometrics import sealed_rows


def rows(seed: int, count: int = 6, dim: int = 128) -> np.ndarray:
    data = np.random.default_rng(seed).standard_normal((count, dim)).astype(np.float32)
    return data / np.linalg.norm(data, axis=1, keepdims=True)


class SealedRowsTest(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        self.env = mock.patch.dict(os.environ, {"NUXIVA_BIOMETRIC_KEY": str(self.root / "etc" / "biometrics.key")})
        self.env.start()
        self.addCleanup(self.env.stop)
        self.folder = self.root / "faces" / "anna"
        self.folder.mkdir(parents=True)
        self.path = self.folder / "embeddings.npy"

    def test_round_trip_keeps_rows(self):
        data = rows(1)
        sealed_rows.save(self.path, data)
        np.testing.assert_allclose(sealed_rows.load(self.path), data)

    def test_disk_holds_no_plaintext(self):
        data = rows(2)
        sealed_rows.save(self.path, data)
        blob = self.path.read_bytes()
        self.assertTrue(blob.startswith(sealed_rows.MAGIC))
        self.assertNotIn(sealed_rows.LEGACY, blob)
        self.assertNotIn(data.tobytes()[:64], blob)
        self.assertTrue(sealed_rows.is_sealed(self.path))

    def test_files_and_key_are_private(self):
        sealed_rows.save(self.path, rows(3))
        self.assertEqual(stat.S_IMODE(self.path.stat().st_mode), 0o600)
        self.assertEqual(stat.S_IMODE(sealed_rows.key_path().stat().st_mode), 0o600)
        self.assertEqual(len(sealed_rows.key_path().read_bytes()), sealed_rows.KEY_LEN)

    def test_loose_key_permissions_are_tightened(self):
        sealed_rows.save(self.path, rows(4))
        sealed_rows.key_path().chmod(0o644)
        sealed_rows.load(self.path)
        self.assertEqual(stat.S_IMODE(sealed_rows.key_path().stat().st_mode), 0o600)

    def test_tampering_is_detected(self):
        sealed_rows.save(self.path, rows(5))
        blob = bytearray(self.path.read_bytes())
        blob[-1] ^= 0x01
        self.path.write_bytes(bytes(blob))
        with self.assertRaises(sealed_rows.SealedRowsError):
            sealed_rows.load(self.path)

    def test_file_moved_to_another_person_is_rejected(self):
        sealed_rows.save(self.path, rows(6))
        other = self.root / "faces" / "marco"
        other.mkdir()
        (other / "embeddings.npy").write_bytes(self.path.read_bytes())
        with self.assertRaises(sealed_rows.SealedRowsError):
            sealed_rows.load(other / "embeddings.npy")

    def test_foreign_key_cannot_open(self):
        sealed_rows.save(self.path, rows(7))
        with mock.patch.dict(os.environ, {"NUXIVA_BIOMETRIC_KEY": str(self.root / "other.key")}):
            with self.assertRaises(sealed_rows.SealedRowsError):
                sealed_rows.load(self.path)

    def test_legacy_plaintext_is_migrated(self):
        data = rows(8)
        np.save(self.path, data)
        np.testing.assert_allclose(sealed_rows.load(self.path), data)
        self.assertTrue(sealed_rows.is_sealed(self.path))
        np.testing.assert_allclose(sealed_rows.load(self.path), data)

    def test_pickled_legacy_payload_is_refused(self):
        np.save(self.path, np.array([{"x": 1}], dtype=object), allow_pickle=True)
        with self.assertRaises(sealed_rows.SealedRowsError):
            sealed_rows.load(self.path)

    def test_unknown_format_is_refused(self):
        self.path.write_bytes(b"garbage")
        with self.assertRaises(sealed_rows.SealedRowsError):
            sealed_rows.load(self.path)

    def test_invalid_rows_are_refused(self):
        for bad in (np.full((2, 4), np.nan, dtype=np.float32), np.zeros((2, 2, 2), dtype=np.float32), np.array([[1, 2]])):
            with self.assertRaises(sealed_rows.SealedRowsError):
                sealed_rows.save(self.path, bad)

    def test_oversized_file_is_refused(self):
        with mock.patch.object(sealed_rows, "MAX_FILE", 16):
            sealed_rows.save(self.path, rows(9))
            with self.assertRaises(sealed_rows.SealedRowsError):
                sealed_rows.load(self.path)

    def test_missing_file_returns_none(self):
        self.assertIsNone(sealed_rows.load(self.folder / "embeddings_ir.npy"))

    def test_software_fallback_interoperates_with_native(self):
        if not sealed_rows.native_ready():
            self.skipTest("nuxiva_native non disponibile")
        data = rows(10)
        sealed_rows.save(self.path, data)
        sealed_rows._keys.clear()
        with mock.patch.object(sealed_rows, "nuxiva_native", None):
            np.testing.assert_allclose(sealed_rows.load(self.path), data)
            sealed_rows.save(self.path, data)
        sealed_rows._keys.clear()
        np.testing.assert_allclose(sealed_rows.load(self.path), data)


class GalleryVaultTest(unittest.TestCase):
    def test_gallery_writes_sealed_embeddings(self):
        from features.vision import gallery as gallery_module
        root = Path(tempfile.mkdtemp())
        with mock.patch.dict(os.environ, {"NUXIVA_BIOMETRIC_KEY": str(root / "biometrics.key")}), \
                mock.patch.object(gallery_module, "FACES", root / "faces"):
            gallery = gallery_module.Gallery()
            gallery.save("Anna", list(rows(11)), np.zeros((8, 8, 3), dtype=np.uint8), ir=list(rows(12, 3)))
            for name in ("embeddings.npy", "embeddings_ir.npy"):
                self.assertTrue(gallery_module.sealed_rows.is_sealed(root / "faces" / "anna" / name))
            gallery.reload()
            self.assertIn("anna", gallery.people)


if __name__ == "__main__":
    unittest.main()
