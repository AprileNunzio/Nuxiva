import sys
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
for p in (str(_ROOT), str(_ROOT / "installer_wizard" / "backend"), str(_ROOT / "installer_wizard"), str(_ROOT / "server")):
    if p not in sys.path:
        sys.path.insert(0, p)

import native_core
from agenti.nodes import telemetry, telemetry_engine as py

NATIVE = native_core.load() is not None and native_core.symbol("node_nearest") is not None


def at(now, **signals):
    return telemetry.clean_proximity(signals, now)


@unittest.skipUnless(NATIVE, "nuxiva_native non installato")
class ParityTest(unittest.TestCase):
    def test_metrics_match_python(self):
        samples = [
            {"cpu": 140, "ram": 41.234, "power_w": 6.25, "gpu": -5, "charging": True, "evil": 1},
            {"cpu": 12.34, "temp": -80, "uptime": 123456.789, "rtt_ms": 38, "rx_kbps": 1.5, "battery": 77.77},
            {"disk": 99.95, "tx_kbps": 0.04},
        ]
        for raw in samples:
            self.assertEqual(telemetry.clean_metrics(raw), py.clean_metrics(raw), raw)

    def test_proximity_match_python(self):
        for signals in ({"speech": 0.9, "face": 0.1234}, {"audio_level": 2, "screen_on": 1}, {"motion": -3}):
            self.assertEqual(telemetry.clean_proximity(signals, 100.04), py.clean_proximity(signals, 100.04), signals)

    def test_nearest_match_python(self):
        scenarios = [
            [{"id": "phone", "online": True, "proximity": at(100, speech=0.9, audio_level=0.7, face=0.5)},
             {"id": "server", "online": True, "proximity": at(100, speech=0.2, audio_level=0.2)}],
            [{"id": "a", "online": True, "proximity": at(100, speech=0.8, audio_level=0.6)},
             {"id": "b", "online": True, "proximity": at(100, speech=0.79, audio_level=0.6)}],
            [{"id": "old", "online": True, "proximity": at(0, speech=1.0, audio_level=1.0)}],
            [{"id": "off", "online": False, "proximity": at(100, speech=1.0)}],
            [{"id": "x", "online": True, "proximity": at(95, speech=0.6, audio_level=0.5, screen_on=1)},
             {"id": "y", "online": True, "proximity": at(80, speech=0.8, audio_level=0.8)}],
            [],
        ]
        for nodes in scenarios:
            for now in (100.0, 101.0, 120.0):
                self.assertEqual(telemetry.nearest(nodes, now), py.nearest(nodes, now), (nodes, now))

    def test_fallback_when_native_disabled(self):
        import os
        os.environ["NUXIVA_NATIVE"] = "0"
        try:
            self.assertEqual(telemetry.clean_metrics({"cpu": 5}), {"cpu": 5.0})
        finally:
            os.environ.pop("NUXIVA_NATIVE", None)


if __name__ == "__main__":
    unittest.main()
