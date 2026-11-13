import json
import random
import unittest

from agenti.firewall.defense import fallback
from agenti.firewall.defense.geo import Geo, PyTable

try:
    import nuxiva_native
except ImportError:
    nuxiva_native = None

NATIVE = nuxiva_native is not None and hasattr(nuxiva_native, "defense_assess")
KINDS = list(fallback.KINDS)
SEVERITIES = ["low", "medium", "high", "critical"]
SOURCES = ["8.8.8.8", "8.8.4.4", "1.1.1.1", "203.0.113.9", "198.51.100.7", "192.168.1.20", "10.0.0.5", "100.64.3.3",
           "fe80::1", "2001:4860:4860::8888", "::ffff:9.9.9.9", "AA-BB-CC-DD-EE-FF", "bad host", "", "fd00::7", "127.0.0.1",
           "172.16.4.4", "172.32.0.1", "169.254.9.9", "x" * 90, "2001:DB8::1", "0.0.0.0"]
COUNTRIES = ["US", "CN", "RU", "DE", "IT", "ZZ", "us", "", "BR"]
GEO = ("1.0.0.0,1.0.0.255,AU\n8.8.8.0,8.8.8.255,US\n8.8.4.0,8.8.4.255,US\n203.0.113.0,203.0.113.255,CN\n"
       "2001:4860::,2001:4860:ffff:ffff:ffff:ffff:ffff:ffff,US\n9.9.9.0,9.9.9.255,ZZ\n# commento\n")


def scenario(rng: random.Random) -> dict:
    now = 100_000.0
    alerts = [{"kind": rng.choice(KINDS), "severity": rng.choice(SEVERITIES), "src": rng.choice(SOURCES),
               "dst": rng.choice(SOURCES), "count": rng.randint(0, 50), "at": now - rng.uniform(-90, 4000)}
              for _ in range(rng.randint(0, 80))]
    policy = {"autonomy": rng.choice(["observe", "assist", "autonomous"]), "mode": rng.choice(["off", "monitor", "protect", "lockdown"]),
              "window_s": rng.choice([1800.0, 30.0, 7200.0, -1.0]), "min_level": rng.choice(SEVERITIES),
              "block_minutes": rng.choice([1, 15, 60, 240, 0]), "max_minutes": rng.choice([60, 10_080, 0, 999_999]),
              "tarpit": rng.random() < 0.5, "honeypot": rng.random() < 0.3, "quarantine": rng.random() < 0.5,
              "country_block": rng.random() < 0.5, "country_threshold": rng.randint(0, 4),
              "home_countries": rng.sample(["it", "US", " cn "], rng.randint(0, 2)), "max_actions_per_hour": rng.randint(0, 6)}
    return {"now": now, "alerts": alerts, "policy": policy,
            "trusted": rng.sample(["8.8.8.0/24", "192.168.1.20", "aa:bb:cc:dd:ee:ff", "2001:4860::/32", "nonsense", "10.0.0.0/33"], rng.randint(0, 3)),
            "protected": rng.sample(["127.0.0.1", "192.168.1.1", "1.1.1.1"], rng.randint(0, 2)),
            "active": rng.sample(["8.8.4.4", "country:US", "203.0.113.9", "192.168.1.20", "1.1.1.1"], rng.randint(0, 3)),
            "strikes": {s: rng.randint(0, 12) for s in rng.sample(["8.8.8.8", "1.1.1.1", "203.0.113.9"], rng.randint(0, 3))},
            "countries": {s: rng.choice(COUNTRIES) for s in rng.sample(["8.8.8.8", "8.8.4.4", "1.1.1.1", "203.0.113.9", "198.51.100.7"], 4)},
            "recent_actions": rng.randint(0, 5)}


@unittest.skipUnless(NATIVE, "nuxiva_native senza defense_assess")
class DefenseParity(unittest.TestCase):

    def test_assessment_matches_python_fallback(self):
        rng = random.Random(20261113)
        for _ in range(600):
            data = scenario(rng)
            native = json.loads(nuxiva_native.defense_assess(json.dumps(data)))
            self.assertEqual(native, fallback.assess(data), json.dumps(data)[:600])

    def test_invalid_input_is_rejected_by_both(self):
        bad = {"now": 1.0, "alerts": [{"kind": "nope", "severity": "low", "at": 1.0}]}
        with self.assertRaises(ValueError):
            nuxiva_native.defense_assess(json.dumps(bad))
        with self.assertRaises(ValueError):
            fallback.assess(bad)

    def test_geo_lookup_matches_python_table(self):
        native, python = Geo(native=True), Geo(native=False)
        self.assertEqual(native.engine, "rust")
        self.assertEqual(native.parse(GEO), python.parse(GEO))
        probes = ["8.8.8.8", "8.8.4.200", "1.0.0.1", "9.9.9.9", "2001:4860::1", "203.0.113.200", "192.168.1.1", "::ffff:8.8.8.8",
                  "nonsense", "", "0.0.0.0", "255.255.255.255"]
        self.assertEqual([native.lookup(p) for p in probes], [python.lookup(p) for p in probes])
        for code in ("US", "AU", "ZZ", "us", "XX"):
            self.assertEqual(native.ranges(code), python.ranges(code))

    def test_geo_rejects_the_same_corrupt_tables(self):
        for text in ("", "a,b\n", "1.0.0.0,1.0.0.255,AU\n1.0.0.10,1.0.1.0,US\n"):
            with self.assertRaises(ValueError):
                Geo(native=True).parse(text)
            with self.assertRaises(ValueError):
                PyTable().parse(text)


if __name__ == "__main__":
    unittest.main()
