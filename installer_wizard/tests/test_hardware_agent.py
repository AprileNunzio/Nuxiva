import asyncio
import sys
import unittest
from unittest import mock

sys.modules.setdefault("cv2", mock.MagicMock())

from fastapi.testclient import TestClient

import nuxiva_supervisor
from features.hardware.expert import agent as hardware_agent
from features.hardware.model import HardwareDevice
from features.hardware.service import hardware_service

HEADERS = {"X-Nuxiva-Request": "1"}


class HardwareAgentTest(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(nuxiva_supervisor.admin)
        self.client.post("/api/auth/login", json={"username": "admin", "password": "nuxiva"}, headers=HEADERS)

    def test_diagnose_tplink_wifi_adapter(self):
        dev = HardwareDevice(
            id="usb:148f:2573:1-6",
            name="TP-Link TL-WN321G",
            vendor="Ralink",
            vendor_id="148f",
            product_id="2573",
            category="wifi",
            driver="rt73usb",
            interface="wlx940c6d8e35a1",
        )
        status, pkgs, missing_fw = hardware_agent.diagnose(dev)
        self.assertIn("firmware-misc-nonfree", pkgs)
        self.assertIn("firmware-mediatek", pkgs)
        self.assertEqual(missing_fw, "rt73.bin")

    def test_diagnose_bluetooth_adapter(self):
        dev = HardwareDevice(
            id="usb:0a12:0001:1-2",
            name="CSR Bluetooth Dongle",
            vendor="CSR",
            vendor_id="0a12",
            product_id="0001",
            category="bluetooth",
            driver="btusb",
        )
        status, pkgs, missing_fw = hardware_agent.diagnose(dev)
        self.assertIn("bluez", pkgs)
        self.assertIn("pulseaudio-module-bluetooth", pkgs)

    def test_provision_tplink_wifi_success(self):
        dev = HardwareDevice(
            id="usb:148f:2573:1-6",
            name="TP-Link TL-WN321G",
            vendor="Ralink",
            vendor_id="148f",
            product_id="2573",
            category="wifi",
            driver="rt73usb",
            interface="wlx940c6d8e35a1",
        )

        async def fake_update():
            return 0, "Hit:1 debian"

        async def fake_install(pkgs):
            return 0, "Installed"

        async def fake_activate(d):
            return True

        with mock.patch.object(hardware_agent, "update_packages", fake_update), \
             mock.patch.object(hardware_agent, "install_packages", fake_install), \
             mock.patch.object(hardware_agent, "_run_cmd", new=mock.AsyncMock(return_value=(0, ""))), \
             mock.patch.object(hardware_agent, "activate_device", fake_activate):
            res = asyncio.run(hardware_agent.provision(dev))

        self.assertTrue(res)
        self.assertEqual(dev.status, "ready")
        self.assertEqual(dev.status_label, "Pronto all'uso")

    def test_hardware_devices_api(self):
        fake_dev = HardwareDevice(
            id="usb:148f:2573:1-6",
            name="TP-Link TL-WN321G",
            vendor="Ralink",
            vendor_id="148f",
            product_id="2573",
            category="wifi",
            status="ready",
        )
        with mock.patch.object(hardware_service, "_devices", {fake_dev.id: fake_dev}):
            r = self.client.get("/api/hardware/devices", headers=HEADERS)
            self.assertEqual(r.status_code, 200)
            data = r.json()
            self.assertIn("devices", data)
            self.assertEqual(len(data["devices"]), 1)
            self.assertEqual(data["devices"][0]["name"], "TP-Link TL-WN321G")


if __name__ == "__main__":
    unittest.main()
