import unittest
from pathlib import Path
import sys

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

    def test_onboard_esp32_satellite(self):
        req = OnboardNodeRequest(
            target="esp32",
            name="LivingRoom-Mic-ESP32",
            parent_id="virtual_core",
            parent_ip="192.168.1.10",
            usb_port="/dev/ttyUSB0",
            wifi_ssid="HomeMesh_5G",
            wifi_key="secretpass123",
        )
        res = onboard_node(req)
        self.assertEqual(res["target"], "esp32")
        self.assertEqual(res["name"], "LivingRoom-Mic-ESP32")
        self.assertEqual(res["status"], "provisioned")
        self.assertIn("Tier-3", res["tier"])
        self.assertIn("node-esp32", res["node_id"])

        # Verifica che sia presente nella lista nodi
        nodes = list_nodes()
        node_ids = [n["id"] for n in nodes]
        self.assertIn(res["node_id"], node_ids)

        # De-provisioning / rimozione
        del_res = delete_node(res["node_id"])
        self.assertTrue(del_res["removed"])
        self.assertEqual(del_res["status"], "deleted")

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

