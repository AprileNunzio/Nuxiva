import json
import unittest
from pathlib import Path

from agenti.nodes import peer_envelope

FIXTURE = json.loads(
    (Path(__file__).resolve().parents[2] / "native/crates/peer-core/tests/fixtures/locate.json").read_text(encoding="utf-8")
)


class PeerEnvelopeVectorsTest(unittest.TestCase):
    def test_every_case_matches_the_rust_verdict(self):
        trusted = set(FIXTURE["trusted"])
        for case in FIXTURE["cases"]:
            with self.subTest(case["name"]):
                try:
                    peer_envelope.verify_locate(case["envelope"], trusted)
                    got = "ok"
                except ValueError as exc:
                    got = str(exc)
                self.assertEqual(got, case["expect"])

    def test_valid_case_returns_addresses(self):
        case = FIXTURE["cases"][0]
        addrs = peer_envelope.verify_locate(case["envelope"], set(FIXTURE["trusted"]))
        self.assertEqual(addrs, ["192.168.1.20:7000", "nodo-1.local:7000"])

    def test_address_rules(self):
        for bad in ("0.0.0.0:80", "224.0.0.1:80", "10.0.0.1:0", "http://x:80", "-a.b:80", "host", "255.255.255.255:9", "[::]:80"):
            with self.subTest(bad):
                with self.assertRaises(ValueError):
                    peer_envelope.check_addr(bad)
        for good in ("[2001:db8::1]:7000", "nodo-1.local:7000", "10.1.2.3:443"):
            with self.subTest(good):
                peer_envelope.check_addr(good)

    def test_oversize_and_type_confusion(self):
        env = dict(FIXTURE["cases"][0]["envelope"])
        trusted = set(FIXTURE["trusted"])
        for patch in ({"ttl": 99}, {"payload": "x" * 20000}, {"seq": True}, {"sig": "zz"}):
            with self.subTest(patch):
                with self.assertRaises(ValueError):
                    peer_envelope.verify_locate({**env, **patch}, trusted)
        with self.assertRaises(ValueError):
            peer_envelope.verify_locate({**env, "extra": 1}, trusted)


if __name__ == "__main__":
    unittest.main()
