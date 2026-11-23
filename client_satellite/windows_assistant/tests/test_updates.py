import base64
import hashlib
import json
import threading
import unittest
from unittest import mock

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from updates import manifest, releases, updater
from updates.errors import UpdateFailure

INSTALLER = b"MZ" + b"\x00" * 1000
URL = "https://github.com/AprileNunzio/NUXIVA/releases/download/assistant-v1.2.0/Nuxiva_Setup.exe"


def keypair():
    key = Ed25519PrivateKey.generate()
    public = key.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    return key, base64.b64encode(public).decode()


def signed(key, **overrides):
    body = {"version": "1.2.0", "url": URL, "sha256": hashlib.sha256(INSTALLER).hexdigest(), "size": len(INSTALLER)}
    data = json.dumps({**body, **overrides}).encode()
    return data, base64.b64encode(key.sign(data))


class ManifestTest(unittest.TestCase):
    def setUp(self):
        self.key, self.public = keypair()

    def test_a_properly_signed_release_is_accepted_and_checked(self):
        data, signature = signed(self.key)
        release = manifest.verify(data, signature, self.public)
        self.assertEqual(release.version, "1.2.0")
        manifest.check_file(INSTALLER, release)
        with self.assertRaises(manifest.UpdateRejected):
            manifest.check_file(INSTALLER + b"x", release)
        with self.assertRaises(manifest.UpdateRejected):
            manifest.check_file(b"MZ" + b"\x01" * 1000, release)

    def test_tampered_or_foreign_signatures_are_rejected(self):
        data, signature = signed(self.key)
        with self.assertRaises(manifest.UpdateRejected):
            manifest.verify(data.replace(b"1.2.0", b"9.9.9"), signature, self.public)
        other, _public = keypair()
        foreign_data, foreign_signature = signed(other)
        with self.assertRaises(manifest.UpdateRejected):
            manifest.verify(foreign_data, foreign_signature, self.public)
        with self.assertRaises(manifest.UpdateRejected):
            manifest.verify(data, b"non-base64!!", self.public)

    def test_only_official_download_addresses(self):
        for url in ("https://evil.example/Nuxiva_Setup.exe",
                    "https://github.com/someone/NUXIVA/releases/download/assistant-v1.2.0/x.exe",
                    "http://github.com/AprileNunzio/NUXIVA/releases/download/assistant-v1.2.0/x.exe"):
            data, signature = signed(self.key, url=url)
            with self.subTest(url=url), self.assertRaises(manifest.UpdateRejected):
                manifest.verify(data, signature, self.public)

    def test_versions(self):
        self.assertTrue(manifest.newer("1.10.0", "1.9.3"))
        self.assertFalse(manifest.newer("1.1.0", "1.1.0"))
        self.assertFalse(manifest.newer("1.1.0", "1.1"))
        with self.assertRaises(manifest.UpdateRejected):
            manifest.newer("1.x", "1.0")

    def test_embedded_public_key_is_a_valid_ed25519_key(self):
        self.assertEqual(len(base64.b64decode(manifest.PUBLIC_KEY)), 32)


def asset(name):
    return {"name": name, "browser_download_url": f"https://github.com/AprileNunzio/NUXIVA/releases/download/x/{name}"}


SIGNED = [asset("manifest.json"), asset("manifest.sig")]


class LatestTest(unittest.TestCase):
    def pick(self, entries, current="0.1"):
        with mock.patch.object(releases.fetch, "get", return_value=json.dumps(entries).encode()):
            return releases.latest(current, threading.Event())

    def test_the_highest_complete_assistant_release_is_chosen(self):
        found = self.pick([
            {"tag_name": "assistant-v1.2.0", "assets": SIGNED},
            {"tag_name": "assistant-v1.10.0", "assets": SIGNED},
            {"tag_name": "assistant-v2.0.0", "assets": [asset("manifest.json")]},
            {"tag_name": "assistant-v3.0.0", "draft": True, "assets": SIGNED},
            {"tag_name": "assistant-v5.0.0", "prerelease": True, "assets": SIGNED},
            {"tag_name": "other-v4.0.0", "assets": SIGNED},
        ])
        self.assertEqual(found.version, "1.10.0")
        self.assertIn("manifest.sig", found.assets)

    def test_unified_tag_wins_over_legacy_and_is_accepted_in_the_manifest(self):
        found = self.pick([{"tag_name": "assistant-v5.8.3", "assets": SIGNED}, {"tag_name": "v5.8.4", "assets": SIGNED}])
        self.assertEqual(found.version, "5.8.4")
        key, public = keypair()
        url = "https://github.com/AprileNunzio/NUXIVA/releases/download/v5.8.4/Nuxiva_Setup.exe"
        data, signature = signed(key, url=url, version="5.8.4")
        self.assertEqual(manifest.verify(data, signature, public).version, "5.8.4")

    def test_unsigned_newer_release_is_reported_not_ignored(self):
        with self.assertRaises(UpdateFailure) as caught:
            self.pick([{"tag_name": "v5.8.17", "assets": [asset("manifest.json")]}], current="5.8.15")
        self.assertEqual((caught.exception.code, caught.exception.detail), ("release_unsigned", "v5.8.17"))

    def test_nothing_newer_means_no_update(self):
        self.assertIsNone(self.pick([{"tag_name": "v5.8.15", "assets": SIGNED}], current="5.8.15"))

    def test_assets_outside_github_are_dropped(self):
        evil = [{"name": "manifest.json", "browser_download_url": "https://evil.example/manifest.json"}, asset("manifest.sig")]
        self.assertIsNone(self.pick([{"tag_name": "v9.0.0", "assets": evil}]))

    def test_release_list_is_requested_as_json(self):
        with mock.patch.object(releases.fetch, "get", return_value=b"[]") as get:
            releases.latest("1.0", threading.Event())
        self.assertEqual(get.call_args.kwargs["accept"], "application/vnd.github+json")


class StateTest(unittest.TestCase):
    def setUp(self):
        import tempfile
        from pathlib import Path

        self.tmp = tempfile.TemporaryDirectory()
        patcher = mock.patch.object(updater, "STATE_FILE", Path(self.tmp.name) / "state.json")
        patcher.start()
        self.addCleanup(patcher.stop)
        self.addCleanup(self.tmp.cleanup)

    def build(self):
        return updater.Updater(lambda text: None, lambda: None)

    def test_report_is_idle_by_default(self):
        report = self.build().report()
        self.assertEqual((report["channel"], report["state"]), ("windows", "idle"))

    def test_target_reached_marks_success(self):
        first = self.build()
        first.mark(state="installing", target=updater.paths.VERSION)
        second = self.build()
        report = second.report()
        self.assertEqual(report["state"], "idle")
        self.assertGreater(report["last_success"], 0)
        self.assertNotIn("target", report)

    def test_interrupted_run_resets_to_idle(self):
        first = self.build()
        first.mark(state="downloading", target="99.0.0")
        self.assertEqual(self.build().report()["state"], "idle")

    def test_rejected_manifest_is_reported_as_failure(self):
        worker = self.build()
        with mock.patch.object(updater.releases, "latest", side_effect=manifest.UpdateRejected("x")):
            with self.assertRaises(UpdateFailure) as caught:
                worker.cycle()
        worker.fail(caught.exception)
        report = worker.report()
        self.assertEqual((report["state"], report["last_error"]["code"]), ("failed", "invalid_signature"))

    def test_up_to_date_cycle_clears_error(self):
        worker = self.build()
        worker.fail(UpdateFailure("hash_mismatch"))
        with mock.patch.object(updater.releases, "latest", return_value=None):
            worker.cycle()
        report = worker.report()
        self.assertEqual(report["state"], "idle")
        self.assertNotIn("last_error", report)
        self.assertGreater(report["last_check"], 0)

if __name__ == "__main__":
    unittest.main()
