import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from starlette.requests import Request

from agenti.desktop.camera_sessions import camera_owner, require_camera_enabled
from agenti.desktop.display_scope import is_remote_kiosk_active, remote_display_scope
from system_settings_api import DEFAULT_DISPLAY_SETTINGS, get_display_settings, save_display_settings


def make_request(host_ip: str, headers: dict | None = None, scheme: str = "http", cookies: dict | None = None) -> Request:
    raw_headers = [(b"host", b"192.168.1.100:80")]
    if headers:
        for k, v in headers.items():
            raw_headers.append((k.lower().encode(), v.encode()))
    scope = {
        "type": "http",
        "method": "POST",
        "scheme": scheme,
        "path": "/api/display/remote-media/camera",
        "headers": raw_headers,
        "client": (host_ip, 54321),
    }
    req = Request(scope)
    if cookies:
        req._cookies = cookies
    return req


class TestRemoteKioskBackend(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp_dir = Path(self._tmp.name)
        self.patch_dir = patch("system_settings_api._nuxiva_dir", return_value=self.tmp_dir)
        self.patch_dir.start()

    def tearDown(self):
        self.patch_dir.stop()
        self._tmp.cleanup()

    def test_default_display_settings_remote_kiosk_disabled(self):
        self.assertIn("remote_kiosk_enabled", DEFAULT_DISPLAY_SETTINGS)
        self.assertFalse(DEFAULT_DISPLAY_SETTINGS["remote_kiosk_enabled"])
        settings = get_display_settings()
        self.assertFalse(settings["remote_kiosk_enabled"])

    def test_save_display_settings_persists_remote_kiosk(self):
        saved = save_display_settings({"remote_kiosk_enabled": True})
        self.assertTrue(saved["remote_kiosk_enabled"])
        loaded = get_display_settings()
        self.assertTrue(loaded["remote_kiosk_enabled"])

    def test_remote_display_scope_transitions(self):
        req = make_request("192.168.1.55")
        with patch.dict(os.environ, {"NUXIVA_REMOTE_KIOSK": "0", "NUXIVA_KIOSK": "1"}):
            self.assertTrue(remote_display_scope(req))

        with patch.dict(os.environ, {"NUXIVA_REMOTE_KIOSK": "1", "NUXIVA_KIOSK": "1"}):
            self.assertFalse(remote_display_scope(req))

    def test_remote_display_scope_rejects_proxy_headers_zero_trust(self):
        req = make_request("192.168.1.55", headers={"X-Forwarded-For": "10.0.0.1"})
        with patch.dict(os.environ, {"NUXIVA_REMOTE_KIOSK": "1"}):
            self.assertTrue(remote_display_scope(req))

    def test_camera_sessions_owner_http_kiosk(self):
        req = make_request("192.168.1.55", headers={"X-Nuxiva-Request": "1", "Origin": "http://192.168.1.100:80"}, scheme="http")
        with patch.dict(os.environ, {"NUXIVA_REMOTE_KIOSK": "0"}):
            with self.assertRaises(Exception):
                camera_owner(req)

        with patch.dict(os.environ, {"NUXIVA_REMOTE_KIOSK": "1"}):
            owner = camera_owner(req)
            self.assertIsInstance(owner, str)
            self.assertEqual(len(owner), 64)

    def test_require_camera_enabled_respects_remote_kiosk(self):
        with patch.dict(os.environ, {"NUXIVA_REMOTE_CAMERA_PREVIEW": "0", "NUXIVA_REMOTE_KIOSK": "0"}):
            with self.assertRaises(Exception):
                require_camera_enabled()

        with patch.dict(os.environ, {"NUXIVA_REMOTE_CAMERA_PREVIEW": "0", "NUXIVA_REMOTE_KIOSK": "1"}):
            require_camera_enabled()

    def test_is_remote_kiosk_active(self):
        with patch.dict(os.environ, {"NUXIVA_REMOTE_KIOSK": "0"}):
            self.assertFalse(is_remote_kiosk_active())
        with patch.dict(os.environ, {"NUXIVA_REMOTE_KIOSK": "1"}):
            self.assertTrue(is_remote_kiosk_active())
