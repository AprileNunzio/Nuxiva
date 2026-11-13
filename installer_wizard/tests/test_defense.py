import gzip
import tempfile
import time
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

from agenti.firewall import model
from agenti.firewall.defense import engine, fallback, geo as geo_module
from agenti.firewall.defense.guardian import Guardian, policy_view
from agenti.firewall.store import store
from tests.test_firewall_runtime import FirewallBase


def alert(kind, severity, src, at, dst="192.168.1.10"):
    return {"kind": kind, "severity": severity, "src": src, "dst": dst, "count": 4, "at": at}


class FallbackRules(unittest.TestCase):

    def test_attack_profile_and_posture(self):
        now = time.time()
        out = fallback.assess({"now": now, "alerts": [alert("port_scan", "medium", "8.8.8.8", now - 50),
                                                      alert("brute_force", "critical", "8.8.8.8", now - 10)]})
        incident = out["incidents"][0]
        self.assertEqual((incident["stage"], incident["origin"], incident["stages"]), ("intrusion", "internet", ["recon", "intrusion"]))
        self.assertEqual(out["posture"], "attack")
        self.assertEqual(out["actions"][0]["kind"], "block")
        self.assertFalse(out["actions"][0]["auto"])

    def test_trusted_device_is_never_blocked(self):
        now = time.time()
        data = {"now": now, "alerts": [alert("exfiltration", "critical", "192.168.1.30", now)], "trusted": ["192.168.1.30"],
                "policy": {"mode": "protect", "autonomy": "autonomous", "quarantine": True}}
        self.assertEqual([(a["kind"], a["reason"], a["auto"]) for a in fallback.assess(data)["actions"]],
                         [("warn", "trusted_anomaly", False)])

    def test_lan_compromise_is_quarantined_only_when_allowed(self):
        now = time.time()
        data = {"now": now, "alerts": [alert("arp_spoof", "critical", "192.168.1.66", now)],
                "policy": {"mode": "protect", "autonomy": "autonomous"}}
        self.assertEqual(fallback.assess(data)["actions"][0]["kind"], "warn")
        data["policy"]["quarantine"] = True
        self.assertEqual(fallback.assess(data)["actions"][0]["kind"], "quarantine")

    def test_invalid_values_are_rejected(self):
        for bad in ({"now": 1, "alerts": [{"kind": "x", "severity": "low", "at": 1}]},
                    {"now": 1, "policy": {"autonomy": "god"}}, {"now": float("nan")}, {"now": 1, "recent_actions": -1}):
            with self.assertRaises(ValueError):
                fallback.assess(bad)

    def test_engine_falls_back_to_python(self):
        self.assertEqual(engine.assess({"now": 1.0}, native=False)["posture"], "calm")


class PolicyFields(unittest.TestCase):

    def test_defense_options_are_validated(self):
        p = model.policy({"autonomy": "autonomous", "home_countries": "it, de", "country_threshold": 1, "max_actions_per_hour": 0})
        self.assertEqual((p.autonomy, p.home_countries, p.country_threshold, p.max_actions_per_hour), ("autonomous", ["IT", "DE"], 2, 1))
        for bad in ({"autonomy": "total"}, {"home_countries": ["ITA"]}, {"home_countries": ["I1"]}):
            with self.assertRaises(ValueError):
                model.policy(bad)

    def test_policy_view_maps_to_engine(self):
        view = policy_view(model.policy({"mode": "protect", "auto_block_severity": "high"}))
        self.assertEqual((view["mode"], view["min_level"], view["autonomy"]), ("protect", "high", "assist"))
        fallback.assess({"now": 1.0, "policy": view})


class GuardianTests(FirewallBase):

    def test_guardian_tracks_posture_and_skips_protected(self):
        guardian = Guardian()
        now = time.time()
        store.policy = model.policy({"mode": "protect", "autonomy": "autonomous"})
        with mock.patch("agenti.firewall.defense.guardian.system_store") as events:
            result = guardian.evaluate([alert("brute_force", "critical", "198.51.100.7", now),
                                        alert("brute_force", "critical", "192.168.1.1", now)], {"192.168.1.1"}, now)
        self.assertEqual(result["posture"], "attack")
        kinds = {a["target"]: (a["kind"], a["auto"]) for a in result["actions"]}
        self.assertEqual(kinds["192.168.1.1"], ("warn", False))
        self.assertEqual(kinds["198.51.100.7"], ("block", True))
        self.assertTrue(events.event.called)

    def test_strikes_raise_the_duration(self):
        guardian = Guardian()
        now = time.time()
        store.policy = model.policy({"mode": "protect", "autonomy": "autonomous", "auto_block_minutes": 30})
        guardian.strike("198.51.100.7")
        guardian.strike("198.51.100.7")
        result = guardian.evaluate([alert("brute_force", "critical", "198.51.100.7", now)], set(), now)
        self.assertEqual(result["actions"][0]["minutes"], 120)
        self.assertEqual(guardian.recent_actions(time.time()), 2)


class GeoTests(unittest.TestCase):

    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        root = Path(folder.name)
        for name, value in (("GEO_DIR", root), ("TABLE_FILE", root / "country.csv"), ("META_FILE", root / "meta.json")):
            patcher = mock.patch.object(geo_module, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)

    def test_install_and_lookup_without_network(self):
        text = "8.8.8.0,8.8.8.255,US\n2.0.0.0,2.255.255.255,FR\n"
        self.assertEqual(geo_module.install(geo_module.unpack(gzip.compress(text.encode())), "2026-11"), 2)
        table = geo_module.Geo(native=False)
        self.assertEqual(table.load(), 2)
        self.assertEqual(table.countries(["8.8.8.8", "2.3.4.5", "192.168.1.4", "nonsense"]), {"8.8.8.8": "US", "2.3.4.5": "FR"})
        self.assertEqual(table.status()["month"], "2026-11")
        self.assertFalse(table.stale())

    def test_corrupt_archive_is_refused(self):
        with self.assertRaises(geo_module.GeoError):
            geo_module.unpack(b"not gzip")
        with self.assertRaises(ValueError):
            geo_module.install("hello\n", "2026-11")
        self.assertFalse(geo_module.TABLE_FILE.exists())

    def test_months_try_current_then_previous(self):
        self.assertEqual(geo_module.months(datetime(2026, 1, 5, tzinfo=timezone.utc)), ["2026-01", "2025-12"])


if __name__ == "__main__":
    unittest.main()
