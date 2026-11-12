import unittest
from unittest import mock

from fastapi.testclient import TestClient

import nuxiva_supervisor


class WebOSEntryTests(unittest.TestCase):
    def setUp(self):
        patcher = mock.patch("setup_api.done", return_value=True)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_preview_uses_current_desktop_bundle_before_static_mount(self):
        client = TestClient(nuxiva_supervisor.admin)
        desktop = client.get("/")
        preview = client.get("/assets/webos-preview/index.html")
        self.assertEqual(desktop.status_code, 200)
        self.assertEqual(preview.status_code, 200)
        self.assertEqual(preview.content, desktop.content)
        self.assertIn('/assets/', preview.text)
        self.assertEqual(preview.headers["cache-control"], "no-store")

    def test_public_server_does_not_serve_admin_preview(self):
        client = TestClient(nuxiva_supervisor.public)
        response = client.get("/assets/webos-preview/index.html")
        desktop = TestClient(nuxiva_supervisor.admin).get("/")
        self.assertNotEqual(response.content, desktop.content)
