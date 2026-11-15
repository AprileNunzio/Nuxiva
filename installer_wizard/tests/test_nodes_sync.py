import tempfile
import unittest
from pathlib import Path
from unittest import mock

from fastapi import HTTPException
from fastapi.testclient import TestClient

import nuxiva_supervisor
from agenti.nodes.registry import registry
from agenti.shares import archive as shares_archive

HEADERS = {"X-Nuxiva-Request": "1"}


class NodesSyncTest(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp_dir.name)
        self.patcher = mock.patch.object(shares_archive, "ROOT", self.root)
        self.patcher.start()

    def tearDown(self):
        self.patcher.stop()
        self.tmp_dir.cleanup()

    def test_person_folder_creates_isolated_directory_and_readme(self):
        folder = shares_archive.person_folder("Mario Rossi")
        self.assertTrue(folder.is_dir())
        self.assertEqual(folder.name, "mario-rossi")
        self.assertTrue((folder / shares_archive.README).is_file())
        content = (folder / shares_archive.README).read_text(encoding="utf-8")
        self.assertIn("mario-rossi", content)
        self.assertIn("Documenti\\Nuxiva", content)

    def test_sync_endpoints_dual_mode_and_traversal_guards(self):
        folder = shares_archive.person_folder("testuser")
        (folder / "saluto.txt").write_text("Ciao da Nuxiva!", encoding="utf-8")

        from agenti.nodes import sync_routes

        # Test safe target validation
        safe = sync_routes._safe_target(folder, "sub/file.txt")
        self.assertEqual(safe.name, "file.txt")

        with self.assertRaises(HTTPException) as ctx:
            sync_routes._safe_target(folder, "../outside.txt")
        self.assertEqual(ctx.exception.status_code, 400)

        with self.assertRaises(HTTPException) as ctx:
            sync_routes._safe_target(folder, "../../etc/passwd")
        self.assertEqual(ctx.exception.status_code, 400)

        # Test scan files
        files = sync_routes._scan_person_files(folder)
        self.assertEqual(len(files), 1)
        self.assertEqual(files[0]["path"], "saluto.txt")
        self.assertIn("sha256", files[0])

    def test_node_heartbeat_sync_metadata(self):
        client = TestClient(nuxiva_supervisor.public)
        node_info = {"id": "win-node-1", "name": "PC Studio", "person_slug": "nunzio", "settings": {}}
        with mock.patch.object(registry, "authenticate", return_value=node_info), \
             mock.patch.object(registry, "effective", return_value={}), \
             mock.patch.object(registry, "heartbeat", return_value=[]):
            r = client.post(
                "/api/nodes/heartbeat",
                json={"version": "1.0", "hostname": "WIN-DESKTOP", "agent": "desktop"},
                headers={"x-nuxiva-node": "win-node-1", "Authorization": "Bearer fake_token", **HEADERS}
            )
            self.assertEqual(r.status_code, 200)
            data = r.json()
            self.assertIn("sync", data)
            self.assertTrue(data["sync"]["enabled"])
            self.assertEqual(data["sync"]["person_slug"], "nunzio")
            self.assertEqual(data["sync"]["folder"], "Nuxiva")
            self.assertIn("condivisa\\persone\\nunzio", data["sync"]["smb_path"])
