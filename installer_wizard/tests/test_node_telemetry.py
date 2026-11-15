import sys
import tempfile
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
for p in (str(_ROOT), str(_ROOT / "installer_wizard" / "backend"), str(_ROOT / "installer_wizard"), str(_ROOT / "server")):
    if p not in sys.path:
        sys.path.insert(0, p)

from agenti.nodes import telemetry
from server.features.mesh_coordinator.power_probe import PowerProbe, battery_watts


class CleanMetricsTest(unittest.TestCase):
    def test_keeps_known_numeric_fields_and_clamps(self):
        out = telemetry.clean_metrics({"cpu": 140, "ram": 41.234, "power_w": 6.2, "rtt_ms": 33, "gpu": -5, "charging": True})
        self.assertEqual(out["cpu"], 100.0)
        self.assertEqual(out["ram"], 41.2)
        self.assertEqual(out["gpu"], 0.0)
        self.assertEqual(out["charging"], 1.0)
        self.assertEqual(out["power_w"], 6.2)
        self.assertEqual(out["rtt_ms"], 33.0)

    def test_drops_unknown_nan_and_text(self):
        out = telemetry.clean_metrics({"cpu": float("nan"), "ram": "50", "evil": 1, "temp": float("inf")})
        self.assertEqual(out, {})

    def test_non_dict(self):
        self.assertEqual(telemetry.clean_metrics("x"), {})
        self.assertEqual(telemetry.clean_proximity(None), {})


class NearestTest(unittest.TestCase):
    def node(self, ident, now, **signals):
        return {"id": ident, "online": True, "proximity": telemetry.clean_proximity(signals, now)}

    def test_picks_clear_winner(self):
        nodes = [self.node("phone", 100, speech=0.9, audio_level=0.7, face=0.5), self.node("server", 100, speech=0.2, audio_level=0.2)]
        out = telemetry.nearest(nodes, 101)
        self.assertEqual(out["node_id"], "phone")
        self.assertGreater(out["confidence"], 0.3)

    def test_ambiguous_when_close(self):
        nodes = [self.node("a", 100, speech=0.8, audio_level=0.6), self.node("b", 100, speech=0.79, audio_level=0.6)]
        out = telemetry.nearest(nodes, 100)
        self.assertIsNone(out["node_id"])
        self.assertTrue(out["ambiguous"])

    def test_stale_and_offline_ignored(self):
        stale = self.node("old", 0, speech=1.0, audio_level=1.0)
        offline = {**self.node("off", 100, speech=1.0), "online": False}
        out = telemetry.nearest([stale, offline], 100)
        self.assertIsNone(out["node_id"])
        self.assertEqual(out["scores"].get("old"), 0.0)

    def test_nobody_active(self):
        out = telemetry.nearest([self.node("a", 100, speech=0.0, audio_level=0.01)], 100)
        self.assertIsNone(out["node_id"])

    def test_small_clock_skew_is_tolerated(self):
        out = telemetry.nearest([self.node("a", 100.04, speech=0.9, audio_level=0.8)], 100.0)
        self.assertEqual(out["node_id"], "a")

    def test_decay_prefers_fresher(self):
        fresh = self.node("fresh", 100, speech=0.6, audio_level=0.5)
        older = self.node("older", 80, speech=0.8, audio_level=0.8)
        self.assertEqual(telemetry.nearest([fresh, older], 100)["node_id"], "fresh")


class PowerProbeTest(unittest.TestCase):
    def test_rapl_delta_and_wrap(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            domain = root / "intel-rapl:0"
            domain.mkdir()
            energy = domain / "energy_uj"
            clock = {"t": 0.0}
            probe = PowerProbe(rapl_root=root, supply_root=root / "none", clock=lambda: clock["t"])
            energy.write_text("1000000")
            self.assertIsNone(probe.cpu_watts())
            clock["t"], _ = 2.0, energy.write_text("21000000")
            self.assertAlmostEqual(probe.cpu_watts(), 10.0, places=3)
            clock["t"], _ = 4.0, energy.write_text("500")
            self.assertIsNone(probe.cpu_watts())

    def test_battery_fallback(self):
        with tempfile.TemporaryDirectory() as tmp:
            bat = Path(tmp) / "BAT0"
            bat.mkdir()
            (bat / "current_now").write_text("1500000")
            (bat / "voltage_now").write_text("12000000")
            self.assertAlmostEqual(battery_watts(Path(tmp)), 18.0, places=3)
            probe = PowerProbe(rapl_root=Path(tmp) / "x", supply_root=Path(tmp))
            self.assertAlmostEqual(probe.system_watts(None), 18.0, places=3)
            self.assertEqual(PowerProbe(rapl_root=Path(tmp) / "x", supply_root=Path(tmp) / "y").system_watts(30.0), 30.0)


class TopologyTest(unittest.TestCase):
    def test_paired_node_exposes_power_gpu_latency_and_nearest(self):
        import tempfile as _tmp
        import os
        from server.features.mesh_coordinator.p2p_mesh import NuxivaMeshCoordinator
        from mesh_topology import compose_topology

        with _tmp.TemporaryDirectory() as tmp:
            os.environ["NUXIVA_STATE_DIR"] = tmp
            mesh = NuxivaMeshCoordinator(node_id="host")
            now = __import__("time").time()
            paired = [{"id": "pixel", "name": "Pixel", "type": "android", "type_label": "Android", "online": True, "last_seen": now,
                       "ip": "192.168.1.9", "hardware": {"ram_gb": 8, "cores": 8},
                       "metrics": telemetry.clean_metrics({"cpu": 21, "ram": 50, "power_w": 4.5, "rtt_ms": 38, "gpu": 12, "battery": 77, "charging": 0}),
                       "proximity": telemetry.clean_proximity({"speech": 0.9, "audio_level": 0.8, "face": 0.6}, now)}]
            topo = compose_topology(mesh, paired)
            node = next(n for n in topo["nodes"] if n["id"] == "pixel")
            data = node["telemetry"]
            self.assertEqual(data["power_watts"], 4.5)
            self.assertEqual(data["ping_ms"], 38.0)
            self.assertEqual(data["gpu_percent"], 12.0)
            self.assertEqual(data["battery_percent"], 77.0)
            self.assertIs(data["charging"], False)
            self.assertEqual(data["ram_used_gb"], 4.0)
            self.assertEqual(topo["nearest"]["node_id"], "pixel")


if __name__ == "__main__":
    unittest.main()
