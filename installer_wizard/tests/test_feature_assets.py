import tempfile
import unittest
from pathlib import Path
from unittest import mock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from access import require_admin
from feature_assets import icon_file
import registry_api


class FeatureAssetsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.manifest = {"id": "sample", "dir": str(self.root), "icon3d": "./icon.png"}
        (self.root / "icon.png").write_bytes(b"\x89PNG\r\n\x1a\nowned-icon")

    def test_asset_must_be_owned_and_explicitly_declared(self):
        self.assertEqual(icon_file(self.manifest), self.root / "icon.png")
        for declaration in (None, "../private.png", "/etc/passwd", "https://example.test/icon.png"):
            self.assertIsNone(icon_file({**self.manifest, "icon3d": declaration}))
        self.assertIsNone(icon_file({}))

    def test_symlink_cannot_escape_feature_directory(self):
        folder = self.root / "feature"
        folder.mkdir()
        try:
            (folder / "icon.png").symlink_to(self.root / "icon.png")
        except OSError:
            self.skipTest("symlink privileges unavailable")
        self.assertIsNone(icon_file({**self.manifest, "dir": str(folder)}))

    def test_icon_endpoint_requires_authentication_and_has_no_path_leak(self):
        app = FastAPI()
        app.include_router(registry_api.admin_routes)
        client = TestClient(app)
        self.assertEqual(client.get("/api/features/sample/icon").status_code, 401)
        app.dependency_overrides[require_admin] = lambda: "admin"
        with mock.patch.object(registry_api.registry, "scan"), mock.patch.object(registry_api.registry, "features", {"sample": self.manifest}):
            response = client.get("/api/features/sample/icon")
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.content, (self.root / "icon.png").read_bytes())
            self.assertEqual(response.headers["content-type"], "image/png")
            self.assertEqual(response.headers["x-content-type-options"], "nosniff")
            missing = client.get("/api/features/unknown/icon")
            self.assertEqual(missing.status_code, 404)
            self.assertNotIn(str(self.root), missing.text)
