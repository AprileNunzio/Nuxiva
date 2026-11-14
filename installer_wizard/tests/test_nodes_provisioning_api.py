import json
import unittest
from pathlib import Path
import sys
from unittest import mock

_ROOT = Path(__file__).resolve().parents[2]
_BACKEND = _ROOT / "installer_wizard" / "backend"
_SERVER = _ROOT / "server"
for p in (str(_ROOT), str(_BACKEND), str(_SERVER)):
    if p not in sys.path:
        sys.path.insert(0, p)

from node_api import (
    get_usb_ports,
    onboard_node,
    delete_node,
    list_nodes,
    OnboardNodeRequest,
)


class NodesProvisioningApiTests(unittest.TestCase):
    def test_get_usb_ports_returns_list(self):
        ports = get_usb_ports()
        self.assertIsInstance(ports, list)
        for p in ports:
            self.assertIn("device", p)
            self.assertIn("description", p)

    def test_onboard_esp32_refuses_ports_that_were_not_detected(self):
        from fastapi import HTTPException
        req = OnboardNodeRequest(target="esp32", name="Mic", usb_port="/dev/ttyUSB9", wifi_ssid="Casa", wifi_key="")
        with mock.patch("node_api.get_usb_ports", return_value=[{"device": "/dev/ttyUSB0", "description": "x"}]):
            with self.assertRaises(HTTPException) as ctx:
                onboard_node(req, mock.Mock())
        self.assertEqual((ctx.exception.status_code, ctx.exception.detail), (400, "esp32.error.port"))

    def test_onboard_esp32_reports_the_real_provisioning_result(self):
        from agenti.nodes import esp32
        request = mock.Mock()
        request.url.hostname = "nuxiva.local"
        link = mock.Mock()
        result = {"node_id": "esp32-mic-0a0a", "name": "Mic", "fingerprint": "AAAA", "pairing_code": "123456",
                  "firmware": "1.0.0", "flash_encrypted": False}
        req = OnboardNodeRequest(target="esp32", name="Mic", usb_port="/dev/ttyUSB0", wifi_ssid="Casa", wifi_key="")
        with mock.patch("node_api.get_usb_ports", return_value=[{"device": "/dev/ttyUSB0", "description": "x"}]), \
                mock.patch.object(esp32, "open_port", return_value=link), \
                mock.patch.object(esp32, "provision", return_value=result) as provision, \
                mock.patch.dict("agenti.secure.api._active", {"port": 8443}), mock.patch("state.store.event"):
            res = onboard_node(req, request)
        provision.assert_called_once_with(link, "nuxiva.local", 8443, "Casa", "", "Mic")
        link.close.assert_called_once()
        self.assertEqual((res["status"], res["node_id"], res["pairing_code"]), ("enrolled", "esp32-mic-0a0a", "123456"))
        self.assertNotIn("Handshake", json.dumps(res))

    def test_onboard_esp32_maps_provisioning_failures_to_conflicts(self):
        from fastapi import HTTPException
        from agenti.nodes import esp32
        request = mock.Mock()
        request.url.hostname = "nuxiva.local"
        link = mock.Mock()
        req = OnboardNodeRequest(target="esp32", name="Mic", usb_port="/dev/ttyUSB0", wifi_ssid="Casa", wifi_key="")
        with mock.patch("node_api.get_usb_ports", return_value=[{"device": "/dev/ttyUSB0", "description": "x"}]), \
                mock.patch.object(esp32, "open_port", return_value=link), \
                mock.patch.object(esp32, "provision", side_effect=esp32.Esp32Error("esp32.error.timeout")), \
                mock.patch.dict("agenti.secure.api._active", {"port": 8443}):
            with self.assertRaises(HTTPException) as ctx:
                onboard_node(req, request)
        self.assertEqual((ctx.exception.status_code, ctx.exception.detail), (409, "esp32.error.timeout"))
        link.close.assert_called_once()

    def test_onboard_pc_workstation(self):
        req = OnboardNodeRequest(
            target="pc",
            name="Studio-i9-GPU",
            parent_id="virtual_core",
            parent_ip="192.168.1.200",
        )
        res = onboard_node(req)
        self.assertEqual(res["target"], "pc")
        self.assertIn("Tier-1", res["tier"])

        del_res = delete_node(res["node_id"])
        self.assertTrue(del_res["removed"])

    def test_rename_node(self):
        from node_api import rename_node, get_node, RenameNodeRequest
        req = RenameNodeRequest(name="Salotto Principale Nuxiva")
        res = rename_node("node-test-rename", req)
        self.assertEqual(res["status"], "renamed")
        self.assertEqual(res["name"], "Salotto Principale Nuxiva")

        # Verify get_node reflects the custom name
        node = get_node("node-test-rename")
        self.assertEqual(node["name"], "Salotto Principale Nuxiva")



if __name__ == "__main__":
    unittest.main()

