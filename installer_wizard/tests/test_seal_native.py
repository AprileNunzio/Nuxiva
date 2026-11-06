import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

for p in (str(Path(__file__).resolve().parents[1]), str(Path(__file__).resolve().parents[1] / "backend")):
    if p not in sys.path:
        sys.path.insert(0, p)

from cryptography.fernet import Fernet, InvalidToken

import native_core
import sealed

NATIVE = native_core.load()
READY = NATIVE is not None and hasattr(NATIVE, "RustFernet") and hasattr(NATIVE, "SealRejected")
PAYLOADS = [b"", b"x", b"a" * 15, b"a" * 16, b"a" * 17, "privato è ù 😀".encode(), os.urandom(4096)]


@unittest.skipUnless(READY, "modulo nativo seal-core non installato")
class SealParityTest(unittest.TestCase):

    def test_rust_tokens_open_with_python_and_back(self):
        key = Fernet.generate_key()
        rust = sealed.SealedCipher(key)
        python = Fernet(key)
        self.assertIsNotNone(rust._rust)
        for payload in PAYLOADS:
            with self.subTest(size=len(payload)):
                self.assertEqual(python.decrypt(rust.encrypt(payload)), payload)
                self.assertEqual(rust.decrypt(python.encrypt(payload)), payload)
                self.assertEqual(rust.decrypt(rust.encrypt(payload).decode()), payload)

    def test_rust_keys_work_in_python(self):
        key = sealed.SealedCipher.generate_key()
        self.assertEqual(Fernet(key).decrypt(sealed.SealedCipher(key).encrypt(b"ok")), b"ok")

    def test_rejections_raise_invalid_token(self):
        cipher = sealed.SealedCipher(Fernet.generate_key())
        other = sealed.SealedCipher(Fernet.generate_key())
        token = cipher.encrypt(b"segreto")
        tampered = token[:-6] + (b"AAAAAA" if token[-6:] != b"AAAAAA" else b"BBBBBB")
        for bad in (other.encrypt(b"segreto"), tampered, b"", b"gAAAA", b"not base64 !!"):
            with self.subTest(token=bad[:12]):
                with self.assertRaises(InvalidToken):
                    cipher.decrypt(bad)

    def test_ttl_matches_python(self):
        key = Fernet.generate_key()
        cipher = sealed.SealedCipher(key)
        token = Fernet(key).encrypt_at_time(b"x", 1_000)
        with mock.patch("sealed.time.time", return_value=1_005):
            self.assertEqual(cipher.decrypt(token, ttl=10), b"x")
        with mock.patch("sealed.time.time", return_value=1_011):
            with self.assertRaises(InvalidToken):
                cipher.decrypt(token, ttl=10)
        with mock.patch("sealed.time.time", return_value=900):
            with self.assertRaises(InvalidToken):
                cipher.decrypt(token, ttl=10)

    def test_bad_keys_are_refused(self):
        for key in (b"", b"short", b"A" * 44):
            with self.subTest(key=key):
                with self.assertRaises(ValueError):
                    sealed.SealedCipher(key)

    def test_vault_written_by_python_engine_opens_with_rust(self):
        with tempfile.TemporaryDirectory() as tmp:
            vault = sealed.SealedFile(Path(tmp) / "v.vault", Path(tmp) / "v.key")
            with mock.patch.object(native_core, "symbol", return_value=None):
                vault.save({"wifi": "segreto", "n": 3})
            self.assertEqual(vault.load(), {"wifi": "segreto", "n": 3})
            vault.save({"wifi": "nuovo"})
            with mock.patch.object(native_core, "symbol", return_value=None):
                self.assertEqual(vault.load(), {"wifi": "nuovo"})


class SealFallbackTest(unittest.TestCase):

    def test_files_are_private_and_python_engine_works(self):
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(native_core, "symbol", return_value=None):
            vault = sealed.SealedFile(Path(tmp) / "v.vault", Path(tmp) / "v.key")
            vault.save({"a": 1})
            self.assertEqual(vault.load(), {"a": 1})
            for name in ("v.vault", "v.key"):
                self.assertEqual((Path(tmp) / name).stat().st_mode & 0o777, 0o600)
            self.assertNotIn(b'"a"', (Path(tmp) / "v.vault").read_bytes())

    def test_write_private_refuses_symlinked_temp_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "elsewhere"
            target.write_bytes(b"keep")
            (Path(tmp) / "f.key.tmp").symlink_to(target)
            with self.assertRaises(OSError):
                sealed.write_private(Path(tmp) / "f.key", b"data")
            self.assertEqual(target.read_bytes(), b"keep")

    def test_encrypt_requires_bytes(self):
        with self.assertRaises(TypeError):
            sealed.SealedCipher(Fernet.generate_key()).encrypt("testo")


if __name__ == "__main__":
    unittest.main()
