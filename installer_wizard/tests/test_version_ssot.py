import unittest
from pathlib import Path

from fastapi.testclient import TestClient

import nuxiva_supervisor
from config import BACKEND_DIR, VERSION
from pages import render


class VersionSsotTest(unittest.TestCase):
    def test_version_matches_root_file(self):
        root_version_file = BACKEND_DIR.parent.parent / "VERSION"
        self.assertTrue(root_version_file.is_file())
        expected = root_version_file.read_text(encoding="utf-8").strip()
        self.assertEqual(VERSION, expected)
        self.assertEqual(VERSION, "5.4.0")

    def test_render_injects_version_window_global(self):
        html_input = "<!doctype html><html><head></head><body><h1>v{{version}}</h1></body></html>"
        res = render(html_input)
        body = res.body.decode("utf-8")
        self.assertIn(f'window.NUXIVA_VERSION = "{VERSION}"', body)
        self.assertIn(f"<h1>v{VERSION}</h1>", body)

    def test_update_status_returns_ssot_version(self):
        from unittest import mock
        import setup_api
        client = TestClient(nuxiva_supervisor.public)
        with mock.patch.object(setup_api, "_private_client", lambda r: True), \
             mock.patch.object(setup_api, "is_local", lambda r: True):
            res = client.get("/api/setup/update", headers={"X-Nuxiva-Request": "1"})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["version"], VERSION)


if __name__ == "__main__":
    unittest.main()
