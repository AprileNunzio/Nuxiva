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


if __name__ == "__main__":
    unittest.main()
