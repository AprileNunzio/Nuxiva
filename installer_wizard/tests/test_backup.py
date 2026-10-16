import tarfile
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from features.backup import service


class BackupTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        base = Path(self.tmp.name)
        (base / "state").mkdir()
        (base / "state" / "data.json").write_text('{"a": 1}')
        (base / "state" / "backups").mkdir()
        (base / "state" / "backups" / "skip.txt").write_text("x")
        self.patches = [mock.patch.object(service, "STATE_DIR", base / "state"), mock.patch.object(service, "ROOT", base / "state" / "backups"),
                        mock.patch.object(service, "INDEX", base / "state" / "backups" / "index.json")]
        for patch in self.patches:
            patch.start()

    def tearDown(self):
        for patch in self.patches:
            patch.stop()
        self.tmp.cleanup()

    async def test_create_contains_state_but_not_backups(self):
        row = await service.create()
        with tarfile.open(service.path_of(row["id"])) as archive:
            names = archive.getnames()
        self.assertIn("state/data.json", names)
        self.assertFalse([n for n in names if "backups" in n])
        self.assertEqual(service.path_of(row["id"]).stat().st_mode & 0o777, 0o600)

    async def test_verify_detects_tampering(self):
        row = await service.create()
        self.assertTrue((await service.verify(row["id"]))["ok"])
        with service.path_of(row["id"]).open("ab") as handle:
            handle.write(b"x")
        self.assertFalse((await service.verify(row["id"]))["ok"])

    async def test_prune_keeps_limit(self):
        with mock.patch.object(service, "keep", return_value=2):
            for _ in range(4):
                await service.create()
        self.assertEqual(len(service.listing()), 2)

    async def test_delete_and_invalid_id(self):
        row = await service.create()
        service.delete(row["id"])
        self.assertEqual(service.listing(), [])
        with self.assertRaises(KeyError):
            service.path_of("../../etc/passwd")

    def test_next_respects_interval(self):
        with mock.patch.object(service, "interval_hours", return_value=0):
            self.assertIsNone(service._next([]))
        with mock.patch.object(service, "interval_hours", return_value=6):
            self.assertEqual(service._next([{"created": 100.0}]), 100.0 + 6 * 3600)


if __name__ == "__main__":
    unittest.main()
