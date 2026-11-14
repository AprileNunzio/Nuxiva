import os
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

from screenshot import rules, sink
from screenshot.service import Service
from screenshot.spool import Spool, delay

WHEN = datetime(2026, 11, 14, 19, 20, 0, tzinfo=timezone.utc)


class RulesTest(unittest.TestCase):
    def test_file_name_has_host_date_and_time(self):
        name = rules.file_name("PC Cucina!", WHEN, 7)
        self.assertEqual(name, "pc-cucina_20261114-192000_007.png")
        self.assertTrue(rules.is_managed(name))
        self.assertEqual(rules.stamp(name), WHEN.timestamp())
        self.assertEqual(rules.host_label("../../x"), "x")
        self.assertEqual(rules.host_label("***"), "nodo")

    def test_unmanaged_names_are_rejected(self):
        for name in ("../a.png", "notes.png", "pc_20261114-192000_007.jpg", "A_20261114-192000_007.png", "a/b_20261114-192000_007.png"):
            self.assertFalse(rules.is_managed(name), name)

    def test_subdir_validation(self):
        self.assertTrue(rules.valid_subdir("05 Scambio/Screenshot"))
        self.assertTrue(rules.valid_subdir(""))
        for bad in ("../x", "a/../b", "/abs", "a//b", ".hidden", "a\\b", "a/b/c/d/e", "x."):
            self.assertFalse(rules.valid_subdir(bad), bad)

    def test_targets(self):
        self.assertEqual(rules.parse_target("smb://nas.local/condivisa"), ("nas.local", "condivisa", ""))
        self.assertEqual(rules.parse_target("z:\\"), ("", "", "Z:"))
        for bad in ("smb://-x/s", "smb://h/a b", "smb://h", "/etc", "C:\\Windows", ""):
            self.assertEqual(rules.parse_target(bad), ("", "", ""), bad)

    def test_settings_to_config(self):
        config = rules.from_settings({
            "NUXIVA_SCREENSHOT": "1", "NUXIVA_SCREENSHOT_TARGET": "smb://nas/condivisa",
            "NUXIVA_SCREENSHOT_MASK": "0,0,1000,50;bad;10,990,200,100", "NUXIVA_SCREENSHOT_RETENTION_DAYS": "7",
            "NUXIVA_SCREENSHOT_BLOCK_GUESTS": "0", "NUXIVA_UI_LANG": "fr"})
        self.assertTrue(config.active)
        self.assertEqual(len(config.masks), 1)
        self.assertEqual((config.days, config.block_guests, config.block_locked, config.lang), (7, False, True, "fr"))
        self.assertEqual(rules.from_settings({"NUXIVA_SCREENSHOT": "1", "NUXIVA_SCREENSHOT_SUBDIR": "../x"}), rules.Config())
        self.assertFalse(rules.from_settings({}).enabled)

    def test_retention(self):
        now = WHEN.timestamp()
        entries = [(rules.file_name("a", datetime.fromtimestamp(now - d * 86400, timezone.utc), i), now - d * 86400)
                   for i, d in enumerate((40, 5, 4, 1))]
        self.assertEqual(rules.doomed(entries, 30, 100, now), [entries[0][0]])
        self.assertEqual(rules.doomed(entries, 0, 2, now), [entries[0][0], entries[1][0]])
        self.assertEqual(rules.doomed(entries, 0, 100, now), [])


class SinkTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_atomic_put_and_idempotence(self):
        directory = sink.resolve(self.root, "05 Scambio/Screenshot")
        name = rules.file_name("pc", WHEN, 1)
        sink.put(directory, name, b"png")
        sink.put(directory, name, b"other")
        self.assertEqual((directory / name).read_bytes(), b"png")
        self.assertEqual(sorted(p.name for p in directory.iterdir()), [name])
        self.assertEqual([n for n, _ in sink.listing(directory)], [name])
        sink.remove(directory, name)
        self.assertFalse((directory / name).exists())

    def test_traversal_is_refused(self):
        directory = sink.resolve(self.root, "ok")
        for name in ("../evil.png", "evil.sh", "a\\b.png"):
            with self.assertRaises(sink.SinkError):
                sink.put(directory, name, b"x")
            with self.assertRaises(sink.SinkError):
                sink.remove(directory, name)
        for sub in ("../up", "a/../b", "/abs"):
            with self.assertRaises(sink.SinkError):
                sink.resolve(self.root, sub)

    @unittest.skipIf(os.name == "nt", "symlink needs privileges")
    def test_symlink_subdir_is_refused(self):
        outside = tempfile.TemporaryDirectory()
        self.addCleanup(outside.cleanup)
        os.symlink(outside.name, self.root / "link")
        with self.assertRaises(sink.SinkError):
            sink.resolve(self.root, "link")
        self.assertEqual(os.listdir(outside.name), [])


class SpoolTest(unittest.TestCase):
    def test_retry_with_backoff_then_delivery(self):
        with tempfile.TemporaryDirectory() as tmp:
            spool = Spool(Path(tmp) / "q")
            spool.enqueue(rules.file_name("pc", WHEN, 1), b"a")
            spool.enqueue(rules.file_name("pc", WHEN, 2), b"b")
            calls = []

            def down(name, data):
                calls.append(name)
                raise sink.SinkError("down")

            self.assertEqual(spool.flush(down, now=100.0), (0, True))
            self.assertEqual(spool.flush(down, now=101.0), (0, False))
            self.assertEqual(len(calls), 1)
            sent = []
            self.assertEqual(spool.flush(lambda n, d: sent.append(n), now=110.0), (2, False))
            self.assertEqual(len(sent), 2)
            self.assertEqual(spool.pending(), [])
            self.assertEqual((delay(0), delay(3), delay(40)), (5, 40, 900))

    def test_spool_is_bounded(self):
        with tempfile.TemporaryDirectory() as tmp:
            spool = Spool(Path(tmp) / "q")
            for i in range(70):
                spool.enqueue(rules.file_name("pc", datetime.fromtimestamp(1_794_684_000 + i, timezone.utc), i), b"x")
            self.assertEqual(len(spool.pending()), 64)


class ServiceTest(unittest.TestCase):
    def make(self, tmp, **settings):
        notes = []
        service = Service(Path(tmp) / "q", notes.append, lambda key: key, Path(tmp) / "guests")
        base = {"NUXIVA_SCREENSHOT": "1", "NUXIVA_SCREENSHOT_TARGET": "z:\\"}
        service.apply({**base, **settings})
        return service, notes

    def test_blocked_when_locked_or_with_guests(self):
        with tempfile.TemporaryDirectory() as tmp:
            service, notes = self.make(tmp)
            with mock.patch("screenshot.service.capture.grab") as grab:
                self.assertEqual(service.capture_once(locked=True), "locked")
                (Path(tmp) / "guests").write_text("1")
                self.assertEqual(service.capture_once(locked=False), "guests")
                grab.assert_not_called()
            self.assertEqual(notes, ["screenshot.blocked", "screenshot.blocked"])

    def test_disabled_is_silent(self):
        with tempfile.TemporaryDirectory() as tmp:
            service, notes = self.make(tmp, NUXIVA_SCREENSHOT="0")
            self.assertEqual(service.capture_once(locked=False), "disabled")
            self.assertEqual(notes, [])

    def test_capture_goes_to_the_queue_when_the_share_is_down(self):
        from PIL import Image
        with tempfile.TemporaryDirectory() as tmp:
            service, notes = self.make(tmp, NUXIVA_SCREENSHOT_MASK="0,0,1000,500")
            with mock.patch("screenshot.service.capture.grab", return_value=Image.new("RGB", (40, 20), (200, 200, 200))), \
                    mock.patch.object(Service, "directory", side_effect=sink.SinkError("down")):
                self.assertEqual(service.capture_once(locked=False), "queued")
            self.assertEqual(len(service.spool.pending()), 1)
            self.assertEqual(notes, ["screenshot.queued"])
            data = (service.spool.directory / service.spool.pending()[0][0]).read_bytes()
            image = Image.open(__import__("io").BytesIO(data))
            self.assertEqual(image.getpixel((5, 5)), (0, 0, 0))
            self.assertEqual(image.getpixel((5, 15)), (200, 200, 200))

    def test_capture_is_delivered_to_the_share(self):
        from PIL import Image
        with tempfile.TemporaryDirectory() as tmp:
            service, notes = self.make(tmp)
            share = Path(tmp) / "share"
            share.mkdir()
            with mock.patch("screenshot.service.capture.grab", return_value=Image.new("RGB", (8, 8))), \
                    mock.patch.object(Service, "directory", return_value=sink.resolve(share, "05 Scambio/Screenshot")):
                self.assertEqual(service.capture_once(locked=False), "delivered")
            stored = list((share / "05 Scambio" / "Screenshot").iterdir())
            self.assertEqual(len(stored), 1)
            self.assertTrue(rules.is_managed(stored[0].name))
            self.assertEqual(service.spool.pending(), [])
            self.assertEqual(notes, ["screenshot.saved"])


if __name__ == "__main__":
    unittest.main()
