import unittest
from unittest import mock

from fastapi.testclient import TestClient

import nuxiva_supervisor
from features.bluetooth import adapter
from features.bluetooth.service import service

HEADERS = {"X-Nuxiva-Request": "1"}
READY = {"present": True, "installed": True, "powered": False, "discovering": False, "name": "hci0", "address": ""}


class BluetoothApiTest(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(nuxiva_supervisor.admin)
        self.client.post("/api/auth/login", json={"username": "admin", "password": "nuxiva"}, headers=HEADERS)

    def _refresh(self):
        async def refresh():
            return {"controller": READY, "devices": [], "routing": {}}
        return refresh

    def test_power_requires_auth_and_csrf(self):
        self.assertEqual(TestClient(nuxiva_supervisor.admin).post("/api/bluetooth/power", json={"on": True}).status_code, 401)
        self.assertEqual(self.client.post("/api/bluetooth/power", json={"on": True}).status_code, 403)

    def test_power_validates_body(self):
        for body in ({"on": "yes"}, {}, [True]):
            self.assertEqual(self.client.post("/api/bluetooth/power", json=body, headers=HEADERS).status_code, 400)

    def test_power_without_adapter_conflicts(self):
        with mock.patch.dict(service.state, {"controller": {"present": False}}):
            self.assertEqual(self.client.post("/api/bluetooth/power", json={"on": True}, headers=HEADERS).status_code, 409)

    def test_power_calls_adapter(self):
        calls = []

        async def power(on):
            calls.append(on)

        with mock.patch.dict(service.state, {"controller": READY}), mock.patch.object(adapter, "power", power), \
                mock.patch.object(service, "refresh", self._refresh()):
            r = self.client.post("/api/bluetooth/power", json={"on": True}, headers=HEADERS)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(calls, [True])

    def test_power_adapter_failure_is_reported(self):
        async def power(on):
            raise adapter.BluetoothError("busy")

        with mock.patch.dict(service.state, {"controller": READY}), mock.patch.object(adapter, "power", power):
            self.assertEqual(self.client.post("/api/bluetooth/power", json={"on": False}, headers=HEADERS).status_code, 502)

    def test_prefs_rejects_malformed_payloads(self):
        for body in ([1, 2], {"devices": {"AA:BB:CC:DD:EE:FF": "x"}}, {"output_order": ["nope"]}):
            self.assertEqual(self.client.put("/api/bluetooth/prefs", json=body, headers=HEADERS).status_code, 400)

    def test_device_settings_validate_and_apply(self):
        url = "/api/bluetooth/devices/AA:BB:CC:DD:EE:FF/settings"
        with mock.patch.object(service, "refresh", self._refresh()):
            self.assertEqual(self.client.put(url, json={"deadzone": "x"}, headers=HEADERS).status_code, 400)
            self.assertEqual(self.client.put(url, json={"unknown": 1}, headers=HEADERS).status_code, 400)
            self.assertEqual(self.client.put("/api/bluetooth/devices/nope/settings", json={}, headers=HEADERS).status_code, 400)
            r = self.client.put(url, json={"voice_input": "preferred"}, headers=HEADERS)
        self.assertEqual(r.status_code, 200)
        self.assertTrue(any(s["key"] == "voice_input" for s in r.json()["schema"]))

    def test_device_settings_require_csrf(self):
        r = self.client.put("/api/bluetooth/devices/AA:BB:CC:DD:EE:FF/settings", json={"vibration": False})
        self.assertEqual(r.status_code, 403)

    def test_unknown_action_and_oversized_body(self):
        self.assertEqual(self.client.post("/api/bluetooth/devices/AA:BB:CC:DD:EE:FF/explode", headers=HEADERS).status_code, 404)
        big = b'{"on": true, "x": "' + b"a" * 9000 + b'"}'
        r = self.client.post("/api/bluetooth/power", content=big, headers={**HEADERS, "Content-Type": "application/json"})
        self.assertEqual(r.status_code, 413)

    def test_gamepads_endpoint_requires_display_access(self):
        public = TestClient(nuxiva_supervisor.public)
        self.assertEqual(public.get("/api/bluetooth/gamepads").status_code, 401)
        with mock.patch("access.is_local", return_value=True):
            r = public.get("/api/bluetooth/gamepads")
        self.assertEqual(r.status_code, 200)
        self.assertIn("gamepads", r.json())


if __name__ == "__main__":
    unittest.main()
