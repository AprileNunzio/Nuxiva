import asyncio
import importlib
import itertools
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from agenti import _genesis, _scaffold
from agenti._registry import AgentRegistry, root

try:
    import nuxiva_native
except ImportError:
    nuxiva_native = None

NATIVE = nuxiva_native is not None and hasattr(nuxiva_native, "agent_genesis_decide")

CALCIO = {"id": "calcio", "category": "sport", "name": "Calcio", "description": "Esperto di calcio, partite e classifiche",
          "capabilities": ["Risultati del calcio", "Classifica del campionato"], "nouns": ["calcio", "partita", "campionato"]}


def python_verdict(hits, taken, motive):
    with mock.patch.object(_genesis, "_native", return_value=None):
        return _genesis.verdict(hits, taken, motive)


class GenesisTest(unittest.TestCase):
    def setUp(self):
        self.base = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.base, True)
        self.registry = AgentRegistry(lambda: [root(self.base, "system", "categorized")], native=False)

    def test_empty_catalog_creates(self):
        verdict = _genesis.decide(CALCIO, registry=self.registry)
        self.assertEqual((verdict["action"], verdict["creatable"]), ("crea", True))

    def test_existing_similar_agent_must_be_enhanced(self):
        _scaffold.create(CALCIO, self.base, self.registry)
        twin = {**CALCIO, "id": "calcio_bis", "name": "Calcio bis"}
        verdict = _genesis.decide(twin, "voglio un altro", self.registry)
        self.assertEqual((verdict["action"], verdict["target"], verdict["creatable"]), ("potenzia", "calcio", False))

    def test_taken_id_is_never_creatable(self):
        _scaffold.create(CALCIO, self.base, self.registry)
        verdict = _genesis.decide({**CALCIO, "description": "altro", "capabilities": [], "nouns": []}, "motivo", self.registry)
        self.assertFalse(verdict["creatable"])
        self.assertEqual(verdict["reason"], "id_taken")

    def test_weak_match_needs_a_motive(self):
        self.assertFalse(python_verdict([("a", 3)], False, False)["creatable"])
        self.assertTrue(python_verdict([("a", 3)], False, True)["creatable"])

    @unittest.skipUnless(NATIVE, "nuxiva_native non disponibile")
    def test_rust_and_python_agree_on_every_case(self):
        ids = ("a", "b", "c")
        for scores, taken, motive in itertools.product(itertools.product(range(0, 7), repeat=3), (False, True), (False, True)):
            hits = list(zip(ids, scores))
            with self.subTest(hits=hits, taken=taken, motive=motive):
                payload = {"hits": [{"id": i, "score": n} for i, n in hits], "id_taken": taken, "motive": motive}
                self.assertEqual(json.loads(nuxiva_native.agent_genesis_decide(json.dumps(payload))), python_verdict(hits, taken, motive))

    @unittest.skipUnless(NATIVE, "nuxiva_native non disponibile")
    def test_rust_rejects_hostile_input(self):
        for raw in ("{", '{"hits":[{"id":"a","score":-1}]}', '{"extra":1}', "x" * 70000):
            with self.subTest(raw=raw[:20]), self.assertRaises(ValueError):
                nuxiva_native.agent_genesis_decide(raw)


class GenesisToolsTest(unittest.TestCase):
    def setUp(self):
        self.base = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.base, True)
        self.registry = AgentRegistry(lambda: [root(self.base, "system", "categorized")], native=False)
        patches = [mock.patch.object(_genesis, "default_registry", self.registry),
                   mock.patch.object(_genesis.decide, "__defaults__", ("", self.registry)),
                   mock.patch.object(_scaffold.create, "__defaults__", (self.base, self.registry))]
        for patch in patches:
            patch.start()
            self.addCleanup(patch.stop)

    def run_tool(self, tool, **args):
        from agenti.agent import registry
        importlib.import_module("agenti.team.tools")
        return asyncio.run(registry.TOOLS[tool]["fn"](**args))

    def test_tool_creates_then_refuses_a_duplicate(self):
        spec = {k: v for k, v in CALCIO.items()}
        first = self.run_tool("agent_nuovo", **spec)
        self.assertIn("creato", first)
        self.assertTrue((self.base / "sport" / "calcio").is_dir())
        second = self.run_tool("agent_nuovo", **{**spec, "id": "calcio_due", "name": "Calcio due"})
        self.assertIn("agente non creato", second)
        self.assertFalse((self.base / "sport" / "calcio_due").exists())

    def test_valuta_is_read_only(self):
        text = self.run_tool("agent_valuta", id="x", category="sport", name="Nome", description="Cose")
        self.assertIn("decisione: crea", text)
        self.assertEqual(list(self.base.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
