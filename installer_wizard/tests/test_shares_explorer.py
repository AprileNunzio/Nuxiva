import tempfile
import unittest
from pathlib import Path
from unittest import mock
from fastapi.testclient import TestClient

import nuxiva_supervisor
from features.shares import archive

HEADERS = {"X-Nuxiva-Request": "1"}


class SharesExplorerTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.admin = TestClient(nuxiva_supervisor.admin)
        assert cls.admin.post("/api/auth/login", json={"username": "admin", "password": "nuxiva"}, headers=HEADERS).status_code == 200

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name) / "condivisa"
        self.root.mkdir(parents=True, exist_ok=True)
        patcher = mock.patch.object(archive, "ROOT", self.root)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.addCleanup(self.temp_dir.cleanup)

    def test_list_files_and_folders(self):
        # Create test folder and file
        doc_dir = self.root / "01 Documenti"
        doc_dir.mkdir(parents=True, exist_ok=True)
        test_file = doc_dir / "nota.txt"
        test_file.write_text("Ciao Nuxiva!", encoding="utf-8")

        res = self.admin.get("/api/shares/files?subpath=01%20Documenti", headers=HEADERS)
        self.assertEqual(res.status_code, 200, res.text)
        data = res.json()
        self.assertEqual(data["folder"], "01 Documenti")
        self.assertEqual(len(data["items"]), 1)
        item = data["items"][0]
        self.assertEqual(item["name"], "nota.txt")
        self.assertFalse(item["is_dir"])
        self.assertEqual(item["ext"], ".txt")
        self.assertGreater(item["size"], 0)

    def test_get_file_content(self):
        doc_dir = self.root / "01 Documenti"
        doc_dir.mkdir(parents=True, exist_ok=True)
        test_file = doc_dir / "readme.md"
        test_file.write_text("# Intestazione Markdown", encoding="utf-8")

        res = self.admin.get("/api/shares/file?path=01%20Documenti/readme.md", headers=HEADERS)
        self.assertEqual(res.status_code, 200, res.text)
        self.assertEqual(res.text, "# Intestazione Markdown")
        self.assertIn("text/markdown", res.headers.get("content-type", ""))

    def test_create_subfolder(self):
        doc_dir = self.root / "01 Documenti"
        doc_dir.mkdir(parents=True, exist_ok=True)

        res = self.admin.post(
            "/api/shares/create_folder",
            json={"parent": "01 Documenti", "name": "NuovaCartella"},
            headers=HEADERS,
        )
        self.assertEqual(res.status_code, 200, res.text)
        self.assertTrue((doc_dir / "nuovacartella").is_dir() or (doc_dir / "NuovaCartella").is_dir())

    def test_upload_file_to_share(self):
        doc_dir = self.root / "01 Documenti"
        doc_dir.mkdir(parents=True, exist_ok=True)
        content = b"Contenuto binario o testuale del file caricato"
        res = self.admin.put(
            "/api/shares/upload?subpath=01%20Documenti&name=documento.pdf",
            content=content,
            headers={**HEADERS, "Content-Type": "application/pdf"},
        )
        self.assertEqual(res.status_code, 200, res.text)
        data = res.json()
        self.assertTrue(data["ok"])
        self.assertEqual(data["name"], "documento.pdf")
        uploaded_path = doc_dir / "documento.pdf"
        self.assertTrue(uploaded_path.is_file())
        self.assertEqual(uploaded_path.read_bytes(), content)

    def test_path_traversal_blocked(self):
        res = self.admin.get("/api/shares/files?subpath=../../etc", headers=HEADERS)
        self.assertEqual(res.status_code, 400)

        res2 = self.admin.get("/api/shares/file?path=../../etc/passwd", headers=HEADERS)
        self.assertEqual(res2.status_code, 400)

        res3 = self.admin.put("/api/shares/upload?subpath=../../etc&name=hack.sh", content=b"evil", headers=HEADERS)
        self.assertEqual(res3.status_code, 400)


if __name__ == "__main__":
    unittest.main()
