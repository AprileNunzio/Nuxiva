import asyncio
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock
from fastapi.testclient import TestClient

import nuxiva_supervisor
from features.shares import archive, scoped

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

    @unittest.skipUnless(os.open in os.supports_dir_fd, "Scoped share access requires directory descriptors")
    def test_scoped_download_stops_after_revocation(self):
        directory = self.root / archive.FOLDERS["documenti"]
        directory.mkdir()
        (directory / "nota.txt").write_bytes(b"ab")
        record = {"role": "auditor", "shares": {"documenti": "read"}}

        async def check():
            response = scoped.download("documenti", path="nota.txt", user="alice")
            self.assertEqual(response.headers["content-length"], "2")
            self.assertEqual(await anext(response.body_iterator), b"a")
            record["shares"].clear()
            with self.assertRaises(StopAsyncIteration):
                await anext(response.body_iterator)

        with mock.patch.object(scoped, "account", return_value=record), mock.patch.object(scoped, "DOWNLOAD_RECHECK_BYTES", 1):
            asyncio.run(check())

    @unittest.skipUnless(os.open in os.supports_dir_fd, "Scoped share access requires directory descriptors")
    def test_scoped_delete_enforces_grants_and_never_recurses(self):
        directory = self.root / archive.FOLDERS["documenti"]
        directory.mkdir()
        folder = directory / "folder"
        folder.mkdir()
        note = folder / "note.txt"
        note.write_text("keep until authorized", encoding="utf-8")
        (directory / "alias").symlink_to(folder, target_is_directory=True)
        record = {"role": "operator", "shares": {"documenti": "read"}}

        def delete(path, share="documenti"):
            return self.admin.delete(f"/api/shares/scoped/{share}/entry", params={"path": path}, headers=HEADERS)

        with mock.patch.object(scoped, "account", return_value=record):
            self.assertEqual(delete("folder/note.txt").status_code, 403)
            record["shares"]["documenti"] = "write"
            self.assertEqual(delete("folder/note.txt", "scambio").status_code, 403)
            self.assertEqual(delete("../folder/note.txt").status_code, 400)
            self.assertEqual(delete("alias/note.txt").status_code, 404)
            self.assertEqual(delete("alias").status_code, 404)
            self.assertEqual(delete("folder").status_code, 409)
            self.assertTrue(note.is_file())
            self.assertEqual(delete("folder/note.txt").status_code, 200)
            self.assertEqual(delete("folder").status_code, 200)
            self.assertFalse(folder.exists())

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

    @unittest.skipUnless(os.open in os.supports_dir_fd, "Scoped share access requires directory descriptors")
    def test_scoped_reader_can_download_only_from_assigned_share(self):
        documenti = self.root / archive.FOLDERS["documenti"]
        documenti.mkdir()
        (documenti / "note.txt").write_text("allowed", encoding="utf-8")
        scambio = self.root / archive.FOLDERS["scambio"]
        scambio.mkdir()
        private = scambio / "private.txt"
        private.write_text("private", encoding="utf-8")
        (documenti / "link.txt").symlink_to(private)
        bindings = {"alice": {"role": "auditor", "shares": {"documenti": "read"}}}
        with (
            mock.patch("access.session_user", return_value="alice"),
            mock.patch("features.authz.access_control.bindings", return_value=bindings),
        ):
            self.assertEqual(self.admin.get("/api/shares/scoped").json(),
                             {"shares": [{"id": "documenti", "name": "01 Documenti", "can_create": False}]})
            listed = self.admin.get("/api/shares/scoped/documenti")
            self.assertEqual(listed.status_code, 200)
            self.assertEqual(listed.json()["items"], [{"name": "note.txt", "is_dir": False}])
            file = self.admin.get("/api/shares/scoped/documenti/file", params={"path": "note.txt"})
            self.assertEqual(file.content, b"allowed")
            self.assertEqual(self.admin.get("/api/shares/scoped/scambio").status_code, 403)
            for path, status in (("link.txt", 404), ("../05 Scambio/private.txt", 400)):
                blocked = self.admin.get("/api/shares/scoped/documenti/file", params={"path": path})
                self.assertEqual(blocked.status_code, status)
            self.assertEqual(self.admin.get("/api/shares").status_code, 403)

    @unittest.skipUnless(os.open in os.supports_dir_fd, "Scoped share access requires directory descriptors")
    def test_scoped_folder_creation_requires_role_and_write_grant(self):
        directory = self.root / archive.FOLDERS["documenti"]
        directory.mkdir()
        account = {"role": "auditor", "shares": {"documenti": "write"}}
        with (
            mock.patch("access.session_user", return_value="alice"),
            mock.patch("features.authz.access_control.bindings", return_value={"alice": account}),
        ):
            url = "/api/shares/scoped/documenti/folders"
            params = {"name": "Cartella"}
            self.assertEqual(self.admin.post(url, params=params, headers=HEADERS).status_code, 403)
            account.update(role="operator", shares={"documenti": "read"})
            self.assertEqual(self.admin.post(url, params=params, headers=HEADERS).status_code, 403)
            account["shares"]["documenti"] = "write"
            self.assertTrue(self.admin.get("/api/shares/scoped").json()["shares"][0]["can_create"])
            self.assertEqual(self.admin.post(url, params=params, headers=HEADERS).status_code, 201)
            self.assertTrue((directory / "Cartella").is_dir())
            self.assertEqual(self.admin.post(url, params=params, headers=HEADERS).status_code, 409)
            nested = {"name": "Sottocartella", "subpath": "Cartella"}
            created = self.admin.post(url, params=nested, headers=HEADERS)
            self.assertEqual(created.status_code, 201)
            self.assertEqual(created.json()["path"], "Cartella/Sottocartella")
            listed = self.admin.get("/api/shares/scoped/documenti", params={"subpath": "Cartella"})
            self.assertEqual(listed.json()["items"], [{"name": "Sottocartella", "is_dir": True}])
            with mock.patch("features.shares.policy.read", return_value={"readonly": True}):
                self.assertFalse(self.admin.get("/api/shares/scoped").json()["shares"][0]["can_create"])
                self.assertEqual(self.admin.post(url, params={"name": "Bloccata"}, headers=HEADERS).status_code, 403)
            (directory / "Collegamento").symlink_to(self.root, target_is_directory=True)
            self.assertEqual(self.admin.post(url, params={**nested, "subpath": "Collegamento"}, headers=HEADERS).status_code, 404)
            account["shares"] = {}
            self.assertEqual(self.admin.get("/api/shares/scoped/documenti", params={"subpath": "Cartella"}).status_code, 403)

    @unittest.skipUnless(os.open in os.supports_dir_fd, "Scoped share access requires directory descriptors")
    def test_scoped_upload_preserves_existing_file_and_discards_oversized_upload(self):
        directory = self.root / archive.FOLDERS["documenti"]
        directory.mkdir()
        (directory / "nota.txt").write_bytes(b"original")
        bindings = {"alice": {"role": "operator", "shares": {"documenti": "write"}}}
        with (
            mock.patch("access.session_user", return_value="alice"),
            mock.patch("features.authz.access_control.bindings", return_value=bindings),
        ):
            url = "/api/shares/scoped/documenti/file"
            duplicate = self.admin.put(url, params={"name": "nota.txt"}, content=b"replacement", headers=HEADERS)
            self.assertEqual(duplicate.status_code, 409)
            self.assertEqual((directory / "nota.txt").read_bytes(), b"original")
            with mock.patch("features.shares.policy.upload_limit_mb", return_value=0):
                oversized = self.admin.put(url, params={"name": "big.txt"}, content=b"x", headers=HEADERS)
            self.assertEqual(oversized.status_code, 413)
            self.assertFalse((directory / "big.txt").exists())
            uploaded = self.admin.put(url, params={"name": "Nuova nota.txt"}, content=b"new", headers=HEADERS)
            self.assertEqual(uploaded.status_code, 201)
            self.assertEqual((directory / "Nuova nota.txt").read_bytes(), b"new")

            open_directory = scoped._directory

            def revoke_after_open(*args, **kwargs):
                descriptor = open_directory(*args, **kwargs)
                bindings["alice"]["shares"]["documenti"] = "read"
                return descriptor

            with mock.patch.object(scoped, "_directory", side_effect=revoke_after_open):
                revoked = self.admin.put(url, params={"name": "revocato.txt"}, content=b"private", headers=HEADERS)
            self.assertEqual(revoked.status_code, 403)
            self.assertFalse((directory / "revocato.txt").exists())


if __name__ == "__main__":
    unittest.main()
