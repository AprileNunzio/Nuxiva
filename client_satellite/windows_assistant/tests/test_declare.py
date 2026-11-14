import json
import unittest
from pathlib import Path

from connection import declare

VECTORS = Path(__file__).resolve().parents[3] / "native" / "crates" / "node-core" / "tests" / "declare_vectors.json"


class DeclareTest(unittest.TestCase):
    def test_declaration_matches_the_rust_vectors(self):
        for case in json.loads(VECTORS.read_text(encoding="utf-8")):
            self.assertEqual(declare.declare(case["facts"], case["host_full"]), case["expect"])

    def test_local_facts_never_claim_host_scopes_without_the_flag(self):
        found = declare.scopes(declare.local_facts(True), False)
        self.assertIn("audio.capture", found)
        self.assertNotIn("node.host_full", found)
        self.assertIn("node.host_full", declare.scopes(declare.local_facts(True), True))

    def test_ram_is_a_non_negative_integer(self):
        self.assertGreaterEqual(declare.ram_mb(), 0)


if __name__ == "__main__":
    unittest.main()
