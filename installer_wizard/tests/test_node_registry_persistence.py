import os
import sys
import tempfile
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
for p in (str(_ROOT), str(_ROOT / "installer_wizard" / "backend"), str(_ROOT / "server")):
    if p not in sys.path:
        sys.path.insert(0, p)

from server.features.mesh_coordinator.node_registry import NodeRegistryError
from server.features.mesh_coordinator.p2p_mesh import NuxivaMeshCoordinator


class NodeRegistryPersistenceTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self._previous = os.environ.get("NUXIVA_STATE_DIR")
        os.environ["NUXIVA_STATE_DIR"] = self._tmp.name
        self.mesh = NuxivaMeshCoordinator(node_id="pc-host")
        self.mesh.peers["rpi-1"] = {"ip": "192.168.1.40", "type": "satellite", "name": "raspberrypi"}

    def tearDown(self):
        if self._previous is None:
            os.environ.pop("NUXIVA_STATE_DIR", None)
        else:
            os.environ["NUXIVA_STATE_DIR"] = self._previous
        self._tmp.cleanup()

    def _canvas_name(self, mesh, node_id):
        return next(n["name"] for n in mesh.get_mesh_canvas_state()["nodes"] if n["id"] == node_id)

    def test_peer_name_survives_hello_and_telemetry_refresh(self):
        self.mesh.rename_node("rpi-1", "Raspberry Ingresso")
        self.mesh.peers["rpi-1"] = {**self.mesh.peers["rpi-1"], "ip": "192.168.1.40", "last_seen": 1.0}
        self.mesh.telemetry_store["rpi-1"] = {"name": "raspberrypi", "cpu_percent": 12.0}
        self.assertEqual(self._canvas_name(self.mesh, "rpi-1"), "Raspberry Ingresso")
        self.assertEqual(self.mesh.get_node_telemetry("rpi-1")["name"], "Raspberry Ingresso")

    def test_local_name_survives_restart_without_freezing_telemetry(self):
        self.mesh.rename_node("pc-host", "Workstation i9")
        self.assertNotIn("pc-host", self.mesh.telemetry_store)
        restarted = NuxivaMeshCoordinator(node_id="pc-host")
        self.assertEqual(self._canvas_name(restarted, "pc-host"), "Workstation i9")

    def test_binding_survives_restart(self):
        self.mesh.peers["pc-2"] = {"ip": "192.168.1.22", "type": "compute"}
        self.mesh.bind_satellite_to_parent("rpi-1", "192.168.1.40", "pc-2", "192.168.1.22", "audio_pcm")
        restarted = NuxivaMeshCoordinator(node_id="pc-host")
        restarted.peers.update(self.mesh.peers)
        parent = next(n["parent_id"] for n in restarted.get_mesh_canvas_state()["nodes"] if n["id"] == "rpi-1")
        self.assertEqual(parent, "pc-2")

    def test_rejects_invalid_names_and_ids(self):
        for bad in ("", "   ", "x" * 65, "‮​"):
            with self.assertRaises(NodeRegistryError):
                self.mesh.rename_node("rpi-1", bad)
        with self.assertRaises(NodeRegistryError):
            self.mesh.rename_node("../etc/passwd", "ok")

    def test_name_is_normalized(self):
        self.assertEqual(self.mesh.rename_node("rpi-1", "  Cucina​   Nord \n"), "Cucina Nord")


if __name__ == "__main__":
    unittest.main()
