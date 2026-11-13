import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path

from agenti import _manifest
from agenti._registry import SYSTEM_DIR, AgentRegistry, root, standard_roots

try:
    import nuxiva_native
except ImportError:
    nuxiva_native = None

NATIVE = nuxiva_native is not None and hasattr(nuxiva_native, "RustAgentRegistry")

CORPUS = [
    '{"id":"ok_id","name":"  Nome  ","description":"d","capabilities":["a","a"," ",{"name":"b"},{"id":"c"}]}',
    '{"id":"ok_id","name":"x","profile":{"ram_mb":12.5,"vram_mb":2.5,"heavy":true}}',
    '{"id":"ok_id","name":"x","requires":{"ram_gb":0.5,"gpu_vram_gb":"2"}}',
    '{"id":"ok_id","name":"x","profile":{"heavy":1}}',
    '{"id":"ok_id","name":"x","profile":{"project":true,"heavy":false}}',
    '{"id":"ok_id","name":"x","profile":{"project":"si"}}',
    '{"id":"ok_id","name":"x","routing":{"nouns":["Medusa"],"verbs":null,"phrases":"no"}}',
    '{"id":"other","name":"x","category":"sport"}',
    '{"id":"ok_id","name":"x","category":"casa"}',
    '{"id":"ok_id","name":"x","category":"inventata"}',
    '{"id":"ok_id","name":"x","capabilities":[1,null,"z"]}',
    '{"id":"ok_id","name":"\\u001cx"}',
    '{"id":7,"name":"x"}',
    '{"name":"x"}',
    '{"id":"a","name":"x"}',
    '{"id":"ok_id","name":"x","icon":"' + "*" * 17 + '"}',
    '{"id":"ok_id","name":"x","tools":[' + ",".join(['"t%d"' % i for i in range(65)]) + "]}",
    '{"id":"ok_id","name":"x","worker":{"kind":"mcp","concurrency_max":4,"tokens_max":8000,"tool_calls_max":12,"time_ms":60000,"tools_scope":["fs.*"," fs.*","web.get"],"needs_graph":true}}',
    '{"id":"ok_id","name":"x","worker":{}}',
    '{"id":"ok_id","name":"x","worker":null}',
    '{"id":"ok_id","name":"x","worker":"si"}',
    '{"id":"ok_id","name":"x","worker":{"kind":"Bad Kind"}}',
    '{"id":"ok_id","name":"x","worker":{"kind":7,"concurrency_max":-1}}',
    '{"id":"ok_id","name":"x","worker":{"concurrency_max":257,"tokens_max":1.5,"tool_calls_max":true}}',
    '{"id":"ok_id","name":"x","worker":{"time_ms":86400001,"tools_scope":"x","needs_graph":"si"}}',
    '{"id":"ok_id","name":"x","worker":{"tools_scope":[1,"",null,"a\\u0001b"]}}',
    '{"id":"ok_id","name":"x","worker":{"tokens_max":18446744073709551615}}',
    "[]",
    "{",
    "null",
]


@unittest.skipUnless(NATIVE, "modulo nativo non installato")
class AgentRegistryParityTest(unittest.TestCase):
    def assert_same_validation(self, raw: str, folder: str, category):
        rust = json.loads(nuxiva_native.agent_manifest_validate(raw, folder, category))
        self.assertEqual(rust, _manifest.validate(raw, folder, category), raw[:120])

    def test_validation_matches_on_edge_cases(self):
        for raw in CORPUS:
            for category in (None, "creativita", "ignota"):
                self.assert_same_validation(raw, "ok_id", category)

    def test_validation_matches_on_every_shipped_manifest(self):
        for path in sorted(SYSTEM_DIR.glob("*/*/feature.json")):
            for category in (None, path.parent.parent.name):
                self.assert_same_validation(path.read_text(encoding="utf-8"), path.parent.name, category)

    def test_snapshot_matches_on_repository_and_fixture(self):
        base = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, base, True)
        (base / "agenti" / "salute" / "medico").mkdir(parents=True)
        (base / "agenti" / "salute" / "medico" / "feature.json").write_text(
            '{"name":"Medico","description":"Battito, stress e respiro","routing":{"nouns":["battito"]}}')
        (base / "features" / "a-b").mkdir(parents=True)
        (base / "features" / "a-b" / "feature.json").write_text('{"name":"x"}')
        (base / "features" / "medico").mkdir(parents=True)
        (base / "features" / "medico" / "feature.json").write_text('{"name":"Doppio"}')
        os.symlink(SYSTEM_DIR / "creativita" / "particles", base / "features" / "particles")
        fixtures = [root(base / "agenti", "system", "categorized"), root(base / "features", "legacy", "flat")]
        for roots in (fixtures, standard_roots()):
            rust = AgentRegistry(lambda r=roots: r)
            python = AgentRegistry(lambda r=roots: r, native=False)
            self.assertEqual(rust.engine, "rust")
            self.assertEqual(rust.snapshot(), python.snapshot())
            for query in ("Mi mostri una medusa", "che tempo fa domani", "battito e stress", ""):
                self.assertEqual(rust.search(query, 8), python.search(query, 8))


if __name__ == "__main__":
    unittest.main()
