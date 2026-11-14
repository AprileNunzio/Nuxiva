import json
import os
import stat
import tempfile
import unittest
from pathlib import Path

from agenti.mcpclient import engine


class CatalogExportTests(unittest.TestCase):
    def test_write_private_is_atomic_and_owner_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "sub" / "catalog.json"
            engine.write_private(target, "uno")
            engine.write_private(target, "due")
            self.assertEqual(target.read_text(encoding="utf-8"), "due")
            self.assertEqual(stat.S_IMODE(os.stat(target).st_mode), 0o600)
            self.assertEqual([p.name for p in target.parent.iterdir()], ["catalog.json"])

    def test_renewed_keeps_serial_and_moves_window(self):
        catalog = {"version": 1, "serial": 7, "issued_at": 10, "not_after": 20, "servers": []}
        fresh = engine.renewed(catalog, 1000)
        self.assertEqual(fresh["serial"], 7)
        self.assertEqual(fresh["issued_at"], 1000)
        self.assertEqual(fresh["not_after"], 1000 + engine.CATALOG_TTL)
        self.assertEqual(catalog["issued_at"], 10)
        json.dumps(fresh)


if __name__ == "__main__":
    unittest.main()
