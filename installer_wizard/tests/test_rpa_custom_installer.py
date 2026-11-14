import asyncio
import hashlib
import json
import re
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from agenti.rpa import custom_installer, releases

CLIENT = Path(__file__).resolve().parents[2] / "client_satellite" / "windows_assistant" / "connection" / "enroll.py"
BASE = b"MZ" + bytes(range(256)) * 40


def info(data=BASE, **extra):
    return {"version": "5.8.1", "name": releases.INSTALLER, "sha256": hashlib.sha256(data).hexdigest(),
            "url": f"{custom_installer.OFFICIAL_PREFIX}assistant-v5.8.1/{releases.INSTALLER}", **extra}


class TrailerTest(unittest.TestCase):
    def test_client_and_server_agree_on_the_marker(self):
        text = CLIENT.read_text(encoding="utf-8")
        self.assertIn(f'TRAILER_MAGIC = b"{custom_installer.MAGIC.decode()}"', text)
        self.assertIn(f"LENGTH_SIZE = {custom_installer.LENGTH_SIZE}", text)

    def test_the_trailer_wraps_the_payload_with_its_length(self):
        payload = json.dumps({"server": "https://x"}).encode()
        block = custom_installer.trailer(payload)
        self.assertTrue(block.endswith(custom_installer.MAGIC))
        self.assertEqual(int.from_bytes(block[-12:-8], "big"), len(payload))
        self.assertEqual(block[:-12], payload)

    def test_empty_or_oversized_payloads_are_refused(self):
        for payload in (b"", b"x" * (custom_installer.PAYLOAD_LIMIT + 1)):
            with self.assertRaises(ValueError):
                custom_installer.trailer(payload)

    def test_the_stream_is_the_clean_installer_followed_by_the_block(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "base.exe"
            path.write_bytes(BASE)
            joined = b"".join(custom_installer.stream(path, b"TAIL"))
        self.assertEqual(joined, BASE + b"TAIL")


class CacheTest(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        patcher = mock.patch.object(custom_installer, "CACHE_DIR", Path(self.folder.name))
        patcher.start()
        self.addCleanup(patcher.stop)
        self.addCleanup(self.folder.cleanup)

    def test_untrusted_metadata_is_refused(self):
        for bad in (info(sha256=""), info(url="https://evil.example/x.exe"), info(version="../../etc")):
            with self.assertRaises(custom_installer.InstallerUnavailable):
                custom_installer._cache_path(bad)

    def test_a_verified_cached_file_is_reused_without_network(self):
        meta = info()
        target = custom_installer._cache_path(meta)
        target.write_bytes(BASE)
        with mock.patch.object(custom_installer, "_download", side_effect=AssertionError("network")):
            self.assertEqual(asyncio.run(custom_installer.base_installer(meta)), target)

    def test_a_tampered_cached_file_is_downloaded_again(self):
        meta = info()
        target = custom_installer._cache_path(meta)
        target.write_bytes(b"tampered")

        async def fake(i, t):
            t.write_bytes(BASE)

        with mock.patch.object(custom_installer, "_download", side_effect=fake):
            path = asyncio.run(custom_installer.base_installer(meta))
        self.assertEqual(path.read_bytes(), BASE)

    def test_old_versions_are_purged(self):
        old = custom_installer.CACHE_DIR / "Nuxiva_Setup-5.0.0-aaaaaaaaaaaaaaaa.exe"
        old.write_bytes(b"old")
        meta = info()

        async def fake(i, t):
            t.write_bytes(BASE)

        with mock.patch.object(custom_installer, "_download", side_effect=fake):
            asyncio.run(custom_installer.base_installer(meta))
        self.assertFalse(old.exists())


class DigestTest(unittest.TestCase):
    def test_release_digest_is_exposed_only_when_well_formed(self):
        digest = "ab" * 32
        tag = "assistant-v5.8.1"
        url = f"https://github.com/{releases.REPOSITORY}/releases/download/{tag}/{releases.INSTALLER}"
        good = {"tag_name": tag, "assets": [{"name": releases.INSTALLER, "browser_download_url": url, "digest": f"sha256:{digest}"}]}
        bad = {"tag_name": tag, "assets": [{"name": releases.INSTALLER, "browser_download_url": url, "digest": "md5:zz"}]}
        self.assertEqual(releases.newest([good])["sha256"], digest)
        self.assertEqual(releases.newest([bad])["sha256"], "")


if __name__ == "__main__":
    unittest.main()
