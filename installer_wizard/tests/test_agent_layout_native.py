import json
import shutil
import tempfile
import unittest
from pathlib import Path

from agenti import _icon, _layout
from agenti._registry import SYSTEM_DIR

try:
    import nuxiva_native
except ImportError:
    nuxiva_native = None

NATIVE = nuxiva_native is not None and hasattr(nuxiva_native, "agent_scaffold")

SPECS = [
    {"id": "medico", "category": "salute", "name": "Medico", "description": "Battito, stress e respiro",
     "capabilities": ["Battito", "Stress"], "nouns": ["battito"], "phrases": ["come sto"], "icon": "🩺"},
    {"id": "calcio", "category": "sport", "name": "Calcio «Serie A»", "description": 'Risultati "live" e \\ statistiche',
     "capabilities": [], "nouns": [], "phrases": [], "icon": ""},
    {"id": "ignoto", "category": "inventata", "name": "x", "description": "y"},
    {"id": "Bad Id", "category": "sport", "name": "x", "description": "y"},
    {"id": "vuoto", "category": "scienza", "name": "x", "description": "   "},
    {"id": "registry", "category": "scienza", "name": "x", "description": "y"},
]


def native_scaffold(spec: dict):
    payload = {"capabilities": [], "nouns": [], "phrases": [], "icon": "", **spec}
    try:
        return [(p, bytes(b)) for p, b in nuxiva_native.agent_scaffold(json.dumps(payload, ensure_ascii=False))]
    except ValueError as exc:
        return sorted(json.dumps(i, sort_keys=True) for i in json.loads(str(exc)))


def python_scaffold(spec: dict):
    try:
        return _layout.scaffold(spec)
    except _layout.ScaffoldError as exc:
        return sorted(json.dumps(i, sort_keys=True) for i in exc.issues)


@unittest.skipUnless(NATIVE, "modulo nativo non installato")
class LayoutParityTest(unittest.TestCase):
    def test_scaffold_is_byte_identical(self):
        for spec in SPECS:
            with self.subTest(id=spec["id"]):
                self.assertEqual(native_scaffold(spec), python_scaffold(spec))

    def test_icons_are_byte_identical(self):
        for category in ("salute", "sport", "creativita", "inventata"):
            for ident in ("medico", "particles", "a" * 40):
                self.assertEqual(bytes(nuxiva_native.agent_icon(category, ident)), _icon.render(category, ident))

    def test_inspect_matches_on_every_shipped_agent_and_partial_trees(self):
        dirs = sorted(p.parent for p in SYSTEM_DIR.glob("*/*/feature.json"))
        temp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, temp, True)
        for rel, body in python_scaffold(SPECS[0])[:5]:
            target = temp / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(body)
        for folder in [*dirs, temp, temp / "assente"]:
            with self.subTest(folder=folder.name):
                self.assertEqual(json.loads(nuxiva_native.agent_layout_inspect(str(folder))), _layout.inspect(folder))


if __name__ == "__main__":
    unittest.main()
