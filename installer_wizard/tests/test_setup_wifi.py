import unittest
from unittest import mock
from fastapi.testclient import TestClient

import nuxiva_supervisor
import setup_api
import setup_wifi


class SetupWifiTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.public = TestClient(nuxiva_supervisor.public)
        self.done_patch = mock.patch.object(setup_api, "done", return_value=False)
        self.private_patch = mock.patch.object(setup_api, "_private_client", lambda r: True)
        self.local_patch = mock.patch.object(setup_api, "is_local", lambda r: True)
        self.done_patch.start()
        self.private_patch.start()
        self.local_patch.start()

    def tearDown(self):
        self.local_patch.stop()
        self.private_patch.stop()
        self.done_patch.stop()

    async def test_cable_status_keys(self):
        cable = setup_wifi.get_cable_status()
        self.assertIn("connected", cable)
        self.assertIn("interface", cable)
        self.assertIn("ip", cable)

    async def test_has_wifi_adapter(self):
        has_adapter, iface = setup_wifi.has_wifi_adapter()
        self.assertIsInstance(has_adapter, bool)
        self.assertIsInstance(iface, str)

    async def test_get_wifi_status_data(self):
        status = await setup_wifi.get_wifi_status()
        self.assertIn("has_wifi", status)
        self.assertIn("is_cable_connected", status)
        self.assertIn("is_optional", status)
        self.assertIn("networks", status)
        self.assertIn("can_proceed", status)

    def test_endpoint_wifi_status_http(self):
        res = self.public.get("/api/setup/wifi/status")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("has_wifi", data)
        self.assertIn("is_cable_connected", data)
        self.assertIn("is_optional", data)

    def test_endpoint_wifi_scan_http(self):
        res = self.public.post("/api/setup/wifi/scan", headers={"X-Nuxiva-Request": "1"})
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data.get("success"))
        self.assertIn("networks", data)

    def test_endpoint_wifi_connect_validation(self):
        res = self.public.post("/api/setup/wifi/connect", json={"ssid": "", "password": ""}, headers={"X-Nuxiva-Request": "1"})
        self.assertEqual(res.status_code, 400)
