from pathlib import Path
import tempfile
import unittest
from unittest import mock

from features.depth_parallax import reconstruct_depth_relief
from features.gaussian_splat import synthesize_gaussian_scene
from features.neural_radiance import synthesize_radiance_scene
from features.particles import (
    ParticleStore,
    codec,
    concept_key,
    decompose_lod,
    extract_hotspots,
    extract_visual_concept,
    point_budget_for,
    show,
    synthesize_spec,
    xr_envelope,
)
from features.visual_catalog import (
    NightDreamSynthesis,
    VisualCatalog,
    classify_academic_entry,
)
from features.visual_router import select_visual_engine


class DedicatedParticlesDirectoryTest(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        self.store = ParticleStore(self.root / "particles")
        self.catalog = VisualCatalog(self.root / "catalog")
        self.dreamer = NightDreamSynthesis(self.catalog)


    def test_dedicated_particles_pipeline(self):
        concept = extract_visual_concept("Come è fatta una medusa?")
        self.assertEqual(concept, "medusa")
        self.assertEqual(concept_key("Medusa!"), "medusa")

        spec = synthesize_spec(concept)
        self.assertGreaterEqual(len(spec["parts"]), 7)
        blob = codec.sample(spec, 512)
        self.assertEqual(codec.count(blob), 512)

        lod = decompose_lod(spec)
        self.assertGreaterEqual(len(lod.shell["parts"]), 2)
        self.assertGreaterEqual(len(lod.core["parts"]), 2)
        self.assertEqual(point_budget_for("shell"), 2500)
        self.assertEqual(point_budget_for("full"), 24000)

        spots = extract_hotspots(concept, spec)
        self.assertGreaterEqual(len(spots), 4)
        labels = {s["label"] for s in spots}
        self.assertIn("Esombrella", labels)
        self.assertIn("Cavità Gastrovascolare", labels)

        brain_spots = extract_hotspots("cervello umano", spec)
        brain_labels = {s["label"] for s in brain_spots}
        self.assertIn("Lobo Frontale", brain_labels)
        self.assertIn("Cervelletto", brain_labels)

        envelope = xr_envelope("a" * 64, "medusa", spots)
        self.assertTrue(envelope["xr_enabled"])
        self.assertEqual(envelope["digest"], "a" * 64)
        self.assertIn("camera", envelope)

        with mock.patch.object(show, "store", self.store):
            show.clear()
            entry = show.ensure_visual("Come è fatta una medusa?")
            self.assertIsNotNone(entry)
            self.assertEqual(entry["concept"], "medusa")
            self.assertEqual(entry["visual_engine"]["selected_engine"], "particles")
            self.assertIn("hotspots", entry)
            self.assertIn("xr", entry)
            self.assertIn("lod_stages", entry)

            cur = show.current()
            self.assertIsNotNone(cur)
            self.assertEqual(cur["concept"], "medusa")
            self.assertIn("hotspots", cur)
            show.clear()

    def test_multi_engine_visual_router_and_generators(self):
        default_route = select_visual_engine("Come è fatta una medusa?")
        self.assertEqual(default_route["selected_engine"], "particles")
        self.assertEqual(default_route["memory_budget_mb"], 4)

        radiance_route = select_visual_engine("Creami una medusa 3d realistico con luci e ombre")
        self.assertEqual(radiance_route["selected_engine"], "neural_radiance")

        splat_route = select_visual_engine("Mostrami un gaussian splat di un cuore")
        self.assertEqual(splat_route["selected_engine"], "gaussian_splat")

        depth_route = select_visual_engine("Trasforma questa immagine in rilievo 3d con parallasse")
        self.assertEqual(depth_route["selected_engine"], "depth_parallax")

        custom_priority = select_visual_engine(
            "Come è fatto un atomo?",
            priority_csv="gaussian_splat,particles",
        )
        self.assertEqual(custom_priority["selected_engine"], "gaussian_splat")

        gs_scene = synthesize_gaussian_scene("medusa", subdiv_per_part=6)
        self.assertEqual(gs_scene["concept"], "medusa")
        self.assertGreaterEqual(len(gs_scene["splats"]), 42)

        nr_scene = synthesize_radiance_scene("medusa")
        self.assertEqual(nr_scene["concept"], "medusa")
        self.assertGreaterEqual(len(nr_scene["nodes"]), 7)
        self.assertEqual(len(nr_scene["key_light"]), 3)

        rgba = bytes([200, 120, 255, 255] * 16)
        relief = reconstruct_depth_relief("medusa", rgba, 4, 4, max_vertices=64)
        self.assertEqual(relief["concept"], "medusa")
        self.assertGreaterEqual(len(relief["vertices"]), 16)

    def test_hierarchical_catalog_and_night_dreamer(self):
        medusa_entry = classify_academic_entry("medusa", "particles", "a" * 64)
        self.assertEqual(
            medusa_entry["relative_dir"],
            "particelle/animali/mare/Rhizostoma_pulmo",
        )
        self.assertIn("Rhizostoma pulmo", medusa_entry["lecture"]["binomial_or_code"])

        v8_entry = classify_academic_entry("motore v8", "gaussian_splat", "b" * 64)
        self.assertEqual(
            v8_entry["relative_dir"],
            "animazioni_3d/auto/motori/motore_v8",
        )

        castello_entry = classify_academic_entry("Castel dell'Ovo", "diorama", "c" * 64)
        self.assertEqual(
            castello_entry["relative_dir"],
            "diorama/castelli/monumenti/Castel_dell_Ovo",
        )

        with mock.patch("features.visual_catalog.night_builder.particle_store", self.store):
            built = self.dreamer.run_idle_cycle(max_items=3)
            self.assertEqual(len(built), 3)
            paths = {item["relative_dir"] for item in built}
            self.assertIn("particelle/animali/mare/Rhizostoma_pulmo", paths)
            self.assertIn("animazioni_3d/auto/motori/motore_v8", paths)
            self.assertIn("diorama/castelli/monumenti/Castel_dell_Ovo", paths)

            medusa_dir = self.root / "catalog" / "particelle/animali/mare/Rhizostoma_pulmo"
            self.assertTrue((medusa_dir / "manifest.json").exists())
            self.assertTrue((medusa_dir / "lecture.json").exists())
            self.assertTrue((medusa_dir / "Rhizostoma_pulmo.nxpc").exists())

            hit_by_concept = self.catalog.lookup("medusa")
            self.assertIsNotNone(hit_by_concept)
            self.assertEqual(
                hit_by_concept["relative_dir"],
                "particelle/animali/mare/Rhizostoma_pulmo",
            )
            hit_by_path = self.catalog.lookup("particelle/animali/mare/Rhizostoma_pulmo")
            self.assertIsNotNone(hit_by_path)
            self.assertEqual(hit_by_path["slug"], "Rhizostoma_pulmo")


if __name__ == "__main__":
    unittest.main()


