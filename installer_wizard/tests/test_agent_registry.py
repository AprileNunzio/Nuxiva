import importlib
import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path

import agenti
from agenti import _manifest, _scan
from agenti._registry import LEGACY_DIR, AgentRegistry, module_for, owner_of, root

PARTICLES = {
    "id": "particles", "name": "Particelle", "category": "creativita", "description": "Scultore di particelle 3D",
    "capabilities": ["Morfogenesi"], "routing": {"nouns": ["medusa", "ologramma"], "phrases": ["mostrami"]},
    "requires": {"ram_gb": 2, "gpu_vram_gb": 1},
}


def write(base: Path, rel: str, body) -> Path:
    path = base / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body if isinstance(body, str) else json.dumps(body), encoding="utf-8")
    return path


class ManifestValidationTest(unittest.TestCase):
    def test_complete_manifest_is_normalized(self):
        report = _manifest.validate(json.dumps(PARTICLES), "particles", "creativita")
        m = report["manifest"]
        self.assertEqual(m["profile"], {"ram_mb": 2048, "vram_mb": 1024, "heavy": False})
        self.assertEqual(m["routing"]["nouns"], ["medusa", "ologramma"])
        self.assertEqual(report["issues"], [])

    def test_structural_errors_reject_the_manifest(self):
        cases = [
            ({"id": "Bad Id", "name": "x"}, "id_invalid"),
            ({"id": "registry", "name": "x"}, "id_reserved"),
            ({"id": "ok_id"}, "name_missing"),
            ({"id": "ok_id", "name": "x", "capabilities": "no"}, "type_list"),
            ({"id": "ok_id", "name": "x\u0007"}, "control_chars"),
            ({"id": "ok_id", "name": "x", "profile": {"ram_mb": -5}}, "out_of_range"),
            ({"id": "ok_id", "name": "x", "routing": []}, "type_object"),
            ({"id": "ok_id", "name": "x", "capabilities": ["y" * 401]}, "too_long"),
        ]
        for raw, code in cases:
            with self.subTest(code=code):
                report = _manifest.validate(json.dumps(raw), "ok_id")
                self.assertIsNone(report["manifest"])
                self.assertIn(code, [i["code"] for i in report["issues"] if i["severity"] == "error"])
        self.assertEqual(_manifest.validate("[1]", "x")["issues"][0]["code"], "not_object")
        self.assertEqual(_manifest.validate("{", "x")["issues"][0]["code"], "invalid_json")
        self.assertEqual(_manifest.validate('{"id":"ab","name":"x","n":NaN}', "ab")["issues"][0]["code"], "invalid_json")
        self.assertEqual(_manifest.validate(" " * 70_000, "x")["issues"][0]["code"], "too_large")

    def test_physical_category_wins_and_mismatch_is_a_warning(self):
        report = _manifest.validate(json.dumps(PARTICLES), "particles", "multimedia")
        self.assertEqual(report["manifest"]["category"], "multimedia")
        self.assertIn("category_folder_mismatch", [i["code"] for i in report["issues"]])


class RegistryScanTest(unittest.TestCase):
    def setUp(self):
        self.base = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.base, True)
        write(self.base, "agenti/creativita/particles/feature.json", PARTICLES)
        write(self.base, "features/particles/feature.json", PARTICLES)
        write(self.base, "features/weather/feature.json", {"id": "weather", "name": "Meteo", "category": "casa"})
        write(self.base, "features/broken/feature.json", "{")
        write(self.base, "features/my-tool/feature.json", {"name": "Con trattino"})
        write(self.base, "outside/evil/feature.json", PARTICLES)
        os.symlink(self.base / "outside" / "evil", self.base / "features" / "evil")
        self.roots = [root(self.base / "agenti", "system", "categorized"), root(self.base / "features", "legacy", "flat")]
        self.registry = AgentRegistry(lambda: self.roots, native=False)

    def test_unique_ids_with_system_precedence(self):
        agents = {a.id: a for a in self.registry.agents()}
        self.assertEqual(sorted(agents), ["particles", "weather"])
        self.assertEqual(agents["particles"].origin, "system")
        self.assertEqual(agents["particles"].category, "creativita")
        codes = {Path(r["path"]).parent.name: [i["code"] for i in r["issues"]] for r in self.registry.rejected()}
        self.assertIn("id_duplicate", codes["particles"])
        self.assertIn("invalid_json", codes["broken"])
        self.assertIn("id_invalid", codes["my-tool"])
        self.assertNotIn("evil", codes)

    def test_discovery_lists_every_manifest_for_panel_validation(self):
        names = [p.parent.name for p in self.registry.manifest_paths()]
        self.assertEqual(sorted(names), ["broken", "my-tool", "particles", "particles", "weather"])

    def test_signature_changes_only_when_files_change(self):
        self.registry.refresh()
        self.assertFalse(self.registry.refresh())
        write(self.base, "agenti/sport/sports/feature.json", {"name": "Sport", "description": "Calcio"})
        self.assertTrue(self.registry.refresh())
        self.assertEqual(self.registry.get("sports").category, "sport")

    def test_search_finds_the_agent_from_a_request(self):
        self.assertEqual(self.registry.search("Mi mostri una medusa")[0][0], "particles")

    def test_package_lookup_refuses_traversal(self):
        self.assertIsNone(self.registry.locate_package("../etc"))
        self.assertEqual(self.registry.locate_package("weather"), self.base / "features" / "weather")


class RepositoryAgentsTest(unittest.TestCase):
    def test_every_shipped_manifest_is_a_valid_agent(self):
        registry = AgentRegistry(native=False)
        self.assertEqual(registry.rejected(), [])
        shipped = {p.parent.name for p in LEGACY_DIR.glob("*/feature.json")}
        shipped |= {p.parent.name for p in (Path(agenti.__file__).parent).glob("*/*/feature.json")}
        self.assertEqual({a.dir.name for a in registry.agents()}, shipped)


class LoaderTest(unittest.TestCase):
    def test_agent_imports_by_id_share_the_module(self):
        first = importlib.import_module("agenti.particles.store")
        second = importlib.import_module("features.particles.store")
        self.assertIs(first, second)

    def test_category_view_resolves_only_its_agents(self):
        self.assertEqual(agenti.creativita.particles.particle_agent.agent_id, "agent.particles.v1")
        with self.assertRaises(AttributeError):
            agenti.multimedia.particles

    def test_category_is_not_an_import_path(self):
        with self.assertRaises(ModuleNotFoundError):
            importlib.import_module("agenti.creativita")

    def test_module_names(self):
        self.assertEqual(module_for(LEGACY_DIR / "particles"), "features.particles")
        self.assertEqual(module_for(Path(agenti.__file__).parent / "creativita" / "particles"), "agenti.particles")
        self.assertEqual(module_for(Path("/tmp/x/particles")), "")
        self.assertEqual(owner_of("agenti.particles.tools"), "particles")
        self.assertEqual(owner_of("os.path"), "")


class FallbackSearchTest(unittest.TestCase):
    def test_repeated_words_count_each_time(self):
        snap = {"keywords": {"medusa": ["particles", "molecules"], "molecola": ["molecules"]}}
        self.assertEqual(_scan.search(snap, "medusa medusa molecola", 5), [("molecules", 3), ("particles", 2)])


if __name__ == "__main__":
    unittest.main()
