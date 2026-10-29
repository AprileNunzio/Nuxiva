import tempfile
import unittest
from pathlib import Path
from unittest import mock

from fastapi.testclient import TestClient

import access
import nuxiva_supervisor
import system_api
from features.desktop.desk import desk

HEADERS = {"X-Nuxiva-Request": "1"}


class DisplaySurfacesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(nuxiva_supervisor.public)

    def setUp(self):
        self.client_is_local = False
        for patch in (mock.patch.object(access, "is_local", lambda request: self.client_is_local),
                      mock.patch.object(system_api, "NUXIVA_DIR", Path(tempfile.mkdtemp())),
                      mock.patch.object(desk, "_save", lambda: None),
                      mock.patch.object(desk, "prefs", {})):
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

    def test_defaults_hide_the_duplicate_voice_meter(self):
        self.assertIs(system_api.get_display_settings()["surfaces"]["rail_voice"], False)

    def test_widget_toggles_need_the_display(self):
        self.assertEqual(self.client.get("/api/display/widgets").status_code, 401)
        self.assertEqual(self.client.put("/api/display/widgets/clock", json={"enabled": False}, headers=HEADERS).status_code, 401)

    def test_widget_toggles_are_validated(self):
        self.client_is_local = True
        desk.scan()
        listing = self.client.get("/api/display/widgets")
        self.assertEqual(listing.status_code, 200, listing.text)
        ids = {w["id"]: w for w in listing.json()["widgets"]}
        self.assertTrue(ids["alarm"]["locked"])
        self.assertEqual(self.client.put("/api/display/widgets/alarm", json={"enabled": False}, headers=HEADERS).status_code, 403)
        self.assertEqual(self.client.put("/api/display/widgets/clock", json={"enabled": "no"}, headers=HEADERS).status_code, 400)
        self.assertEqual(self.client.put("/api/display/widgets/nope", json={"enabled": False}, headers=HEADERS).status_code, 404)
        r = self.client.put("/api/display/widgets/clock", json={"enabled": False}, headers=HEADERS)
        self.assertEqual(r.status_code, 200, r.text)
        self.assertFalse(desk.enabled("clock"))


if __name__ == "__main__":
    unittest.main()
