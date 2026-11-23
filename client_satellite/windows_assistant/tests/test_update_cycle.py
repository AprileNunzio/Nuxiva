import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from updates import manifest, releases, updater
from updates.errors import UpdateFailure

INSTALLER = b"MZ" + b"\x02" * 4096
URL = "https://github.com/AprileNunzio/NUXIVA/releases/download/v9.0.0/Nuxiva_Setup.exe"
RELEASE = manifest.Release("9.0.0", URL, hashlib.sha256(INSTALLER).hexdigest(), len(INSTALLER))
FOUND = releases.Candidate("9.0.0", "v9.0.0", {"manifest.json": "https://github.com/m", "manifest.sig": "https://github.com/s"})


def fake_download(url, target, size, stop):
    Path(target).write_bytes(INSTALLER)
    return hashlib.sha256(INSTALLER).hexdigest()


class CycleTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        for name, value in (("UPDATES_DIR", root), ("STATE_FILE", root / "state.json")):
            patcher = mock.patch.object(updater, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)
        self.notes, self.launched, self.quit = [], [], []
        self.worker = updater.Updater(self.notes.append, lambda: self.quit.append(True), lambda key, **v: key)

    def run_cycle(self, download=fake_download):
        with mock.patch.object(updater.releases, "latest", return_value=FOUND), \
                mock.patch.object(self.worker, "verified", return_value=RELEASE), \
                mock.patch.object(updater.fetch, "download", side_effect=download), \
                mock.patch.object(updater.launcher, "launch", side_effect=lambda path: self.launched.append(path.read_bytes())):
            self.worker.cycle()

    def test_verified_installer_is_launched_and_the_client_restarts(self):
        self.run_cycle()
        self.assertEqual(self.launched, [INSTALLER])
        self.assertEqual(self.quit, [True])
        self.assertEqual(self.worker.report()["state"], "installing")
        self.assertIn("updates.installing", self.notes)

    def test_tampered_file_on_disk_is_never_launched(self):
        def tampered(url, target, size, stop):
            Path(target).write_bytes(b"MZ" + b"\x03" * 4096)
            return RELEASE.sha256

        with self.assertRaises(UpdateFailure) as caught:
            self.run_cycle(tampered)
        self.assertEqual(caught.exception.code, "hash_mismatch")
        self.assertEqual(self.launched, [])
        self.assertEqual(list(Path(self.tmp.name).glob(f"{updater.WORK_PREFIX}*")), [])

    def test_failures_back_off_and_notify_once(self):
        failure = UpdateFailure("server_rejected", "HTTP 415")
        delays = []
        for _ in range(5):
            self.worker.fail(failure)
            delays.append(self.worker.delay())
        self.assertEqual(delays, [300, 900, 3600, 10800, 10800])
        self.assertEqual(self.notes, ["updates.failed"])
        error = self.worker.report()["last_error"]
        self.assertEqual((error["code"], error["detail"]), ("server_rejected", "HTTP 415"))
        state = json.loads((Path(self.tmp.name) / "state.json").read_text())
        self.assertEqual(state["state"], "failed")

    def test_security_failures_always_notify(self):
        self.worker.fail(UpdateFailure("invalid_signature", "bad"))
        self.assertEqual(self.notes, ["updates.rejected"])

    def test_signed_version_must_match_the_release(self):
        other = manifest.Release("9.0.1", URL, RELEASE.sha256, RELEASE.size)
        with mock.patch.object(updater.fetch, "get", return_value=b""), mock.patch.object(updater.manifest, "verify", return_value=other):
            with self.assertRaises(UpdateFailure) as caught:
                self.worker.verified(FOUND)
        self.assertEqual(caught.exception.code, "invalid_signature")


class TranslationTest(unittest.TestCase):
    def test_every_update_message_is_translated(self):
        root = Path(updater.__file__).resolve().parents[1] / "i18n"
        keys = {"updates.installing", "updates.rejected", "updates.failed"} | {
            f"updates.error.{code}" for code in ("network_unreachable", "server_rejected", "release_unsigned", "download_failed",
                                                 "invalid_signature", "hash_mismatch", "storage_full", "storage_failed", "install_blocked")}
        for language in ("it", "en", "fr", "es"):
            table = json.loads((root / f"{language}.json").read_text(encoding="utf-8"))
            with self.subTest(language=language):
                self.assertEqual(keys - table.keys(), set())


if __name__ == "__main__":
    unittest.main()
