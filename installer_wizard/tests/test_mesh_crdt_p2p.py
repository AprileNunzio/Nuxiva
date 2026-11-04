import unittest
from pathlib import Path
import sys

_ROOT = Path(__file__).resolve().parents[2]
_BACKEND = _ROOT / "installer_wizard" / "backend"
_SERVER = _ROOT / "server"
for p in (str(_ROOT), str(_BACKEND), str(_SERVER)):
    if p not in sys.path:
        sys.path.insert(0, p)

from server.features.mesh_coordinator.p2p_mesh import NuxivaMeshCoordinator
from server.core.event_sourcing.ledger import TimeTravelLedger


class MeshCrdtP2PTests(unittest.TestCase):
    def setUp(self):
        self.node_a = NuxivaMeshCoordinator(node_id="pc-node-a")
        self.node_b = NuxivaMeshCoordinator(node_id="pc-node-b")
        self.ledger = TimeTravelLedger(db_path=":memory:", node_id="ledger-test")

    def test_ledger_crdt_event_synchronization(self):
        self.ledger.append_event("device.living_room", "UPDATED", {"brightness": 75, "state": "ON"})
        self.assertEqual(self.ledger.get_crdt_value("device.living_room.brightness"), "75")
        self.assertIn("device.living_room.state", self.ledger.export_crdt_state())

    def test_crdt_virtual_core_settings_replication(self):
        # Imposta una chiave sul nodo A
        self.node_a.set_crdt_setting("household.language", "it")
        self.node_a.set_crdt_setting("energy.profile", "eco")

        # Esporta lo stato di A e fondilo su B
        payload_a = self.node_a.export_crdt_state()
        updated = self.node_b.merge_crdt_state(payload_a)
        self.assertGreaterEqual(updated, 2)

        # Verifica che il nodo B abbia esattamente le stesse impostazioni del Virtual Core
        self.assertEqual(self.node_b.get_crdt_setting("household.language"), "it")
        self.assertEqual(self.node_b.get_crdt_setting("energy.profile"), "eco")

    def test_direct_p2p_offload_zero_bottleneck(self):
        # Associa Raspberry Pi (Satellite) direttamente a PC-i9 con GPU (Parent Node)
        satellite_id = "rpi-living-room"
        satellite_ip = "192.168.1.50"
        parent_id = "pc-i9-gpu"
        parent_ip = "192.168.1.10"

        self.node_a.bind_satellite_to_parent(
            satellite_id=satellite_id,
            satellite_ip=satellite_ip,
            parent_node_id=parent_id,
            parent_ip=parent_ip,
            stream_type="rtsp_video"
        )

        # Risolvi la destinazione diretta del flusso video
        resolved_ip = self.node_a.resolve_stream_destination(satellite_id)
        self.assertEqual(resolved_ip, parent_ip)

        # Registra traffico diretto: 100% transita sul link diretto
        transferred = 5_000_000 # 5 MB
        self.assertTrue(self.node_a.record_direct_stream_traffic(satellite_id, transferred))
        self.assertEqual(self.node_a._bindings[satellite_id]["bytes_transferred"], transferred)

        # Verifica che un altro satellite non configurato non abbia rotte verso nodi non associati
        self.assertIsNone(self.node_a.resolve_stream_destination("unknown-sensor"))

    def test_hover_telemetry_live_hud(self):
        telemetry = self.node_a.get_node_telemetry("pc-node-a")
        self.assertIn("cpu_percent", telemetry)
        self.assertIn("ram_used_gb", telemetry)
        self.assertIn("vram_used_gb", telemetry)
        self.assertIn("power_watts", telemetry)
        self.assertIn("ping_ms", telemetry)
        self.assertIn("status", telemetry)

    def test_mesh_canvas_topology_structure(self):
        state = self.node_a.get_mesh_canvas_state()
        self.assertIn("nodes", state)
        self.assertIn("links", state)
        node_ids = [n["id"] for n in state["nodes"]]
        self.assertIn(self.node_a.node_id, node_ids)

        # Simula registrazione peer reale
        self.node_a.peers["peer-satellite"] = {"ip": "192.168.1.50", "name": "Satellite-1"}
        state_updated = self.node_a.get_mesh_canvas_state()
        updated_node_ids = [n["id"] for n in state_updated["nodes"]]
        self.assertIn("peer-satellite", updated_node_ids)


if __name__ == "__main__":
    unittest.main()
