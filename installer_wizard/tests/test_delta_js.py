import json
import shutil
import subprocess
import unittest
from pathlib import Path

import stream_delta

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "web" / "shared" / "delta.js"
RUNNER = """
require(process.argv[1]);
const { applyOps } = globalThis.NuxivaDelta;
const cases = JSON.parse(require("fs").readFileSync(0, "utf8"));
const out = cases.map(([doc, ops]) => { try { return applyOps(doc, ops); } catch (e) { return { error: e.message }; } });
process.stdout.write(JSON.stringify(out));
"""


@unittest.skipUnless(shutil.which("node"), "node non disponibile")
class DeltaClientTests(unittest.TestCase):

    def run_node(self, cases):
        done = subprocess.run(["node", "-e", RUNNER, str(SCRIPT)], input=json.dumps(cases), capture_output=True,
                              text=True, timeout=30, check=True)
        return json.loads(done.stdout)

    def test_the_browser_applies_server_patches_exactly(self):
        pairs = [({"a": 1, "b": {"c": [1]}, "x": None}, {"a": 2, "b": {"c": [2], "d": {}}, "y": False}),
                 ({"k/j": {"t~": 1}}, {"k/j": {"t~": 2}}), ({"a": {"b": 1}}, {"a": None}), ({}, {"z": "w"})]
        cases = [[old, json.loads(stream_delta.python_diff(json.dumps(old), json.dumps(new)))] for old, new in pairs]
        self.assertEqual(self.run_node(cases), [new for _, new in pairs])

    def test_prototype_pollution_and_bad_ops_are_rejected(self):
        cases = [[{}, [{"op": "add", "path": "/__proto__", "value": {"admin": True}}]],
                 [{"a": 1}, [{"op": "replace", "path": "/missing", "value": 1}]],
                 [{"a": 1}, [{"op": "remove", "path": ""}]],
                 [{"a": 1}, [{"op": "add", "path": "a", "value": 1}]]]
        self.assertTrue(all("error" in r for r in self.run_node(cases)))


if __name__ == "__main__":
    unittest.main()
