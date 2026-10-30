import tempfile
import unittest
from pathlib import Path
from unittest import mock

from fastapi.testclient import TestClient

import access
import nuxiva_supervisor
import system_api

HEADERS = {"X-Nuxiva-Request": "1"}


class DisplaySurfacesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(nuxiva_supervisor.public)

    def setUp(self):
        self.client_is_local = False
        for patch in (mock.patch.object(access, "is_local", lambda request: self.client_is_local),
                      mock.patch.object(system_api, "NUXIVA_DIR", Path(tempfile.mkdtemp()))):
            patch.start()
            self.addCleanup(patch.stop)

    def test_display_settings_cannot_be_changed_from_the_network(self):
        r = self.client.post("/api/system/display-settings", json={"show_clock": False}, headers=HEADERS)
        self.assertEqual(r.status_code, 401)

    def test_surfaces_are_validated_and_merged(self):
        self.client_is_local = True
        r = self.client.post("/api/system/display-settings", headers=HEADERS,
                             json={"surfaces": {"rail_voice": True, "project": "no", "evil": True}, "mic_autocalibrate": False})
        self.assertEqual(r.status_code, 200, r.text)
        saved = r.json()["settings"]
        self.assertIs(saved["surfaces"]["rail_voice"], True)
        self.assertIs(saved["surfaces"]["project"], True)
        self.assertNotIn("evil", saved["surfaces"])
        self.assertIs(saved["mic_autocalibrate"], False)
        again = self.client.post("/api/system/display-settings", headers=HEADERS, json={"surfaces": {"project": False}}).json()["settings"]
        self.assertIs(again["surfaces"]["rail_voice"], True)
        self.assertIs(again["surfaces"]["project"], False)

    def test_token_usage_widget_is_off_until_requested(self):
        self.assertIs(system_api.get_display_settings()["surfaces"]["token_usage"], False)
        self.client_is_local = True
        saved = self.client.post("/api/system/display-settings", headers=HEADERS, json={"surfaces": {"token_usage": True}}).json()["settings"]
        self.assertIs(saved["surfaces"]["token_usage"], True)

    def test_defaults_hide_the_duplicate_voice_meter(self):
        self.assertIs(system_api.get_display_settings()["surfaces"]["rail_voice"], False)


if __name__ == "__main__":
    unittest.main()
