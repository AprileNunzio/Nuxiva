from pathlib import Path
import tempfile
import unittest
from unittest import mock

from agenti.depth_parallax import reconstruct_depth_relief
from agenti.gaussian_splat import synthesize_gaussian_scene
from agenti.neural_radiance import synthesize_radiance_scene
from agenti.particles import (
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
from agenti.visual_catalog import (
    NightDreamSynthesis,
    VisualCatalog,
    classify_academic_entry,
)
from agenti.visual_router import select_visual_engine


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

        with mock.patch("agenti.visual_catalog.night_builder.particle_store", self.store):
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

    def test_independent_autonomous_agents(self):
        from agenti.depth_parallax import depth_parallax_agent
        from agenti.diorama.agent import diorama_agent
        from agenti.gaussian_splat import gaussian_splat_agent
        from agenti.neural_radiance import neural_radiance_agent
        from agenti.particles import particle_agent
        from agenti.visual_router import dispatch_visual_agent

        p_art = particle_agent.run("Come è fatta una medusa?", persist=False)
        self.assertEqual(p_art["agent_id"], "agent.particles.v1")
        self.assertTrue(p_art["critique"]["passed"])
        self.assertEqual(
            p_art["catalog_entry"]["relative_dir"],
            "particelle/animali/mare/Rhizostoma_pulmo",
        )

        d_art = diorama_agent.run("Castel dell'Ovo", persist=False)
        self.assertEqual(d_art["agent_id"], "agent.diorama.v1")
        self.assertEqual(
            d_art["catalog_entry"]["relative_dir"],
            "diorama/castelli/monumenti/Castel_dell_Ovo",
        )

        g_art = gaussian_splat_agent.run("motore v8", persist=False)
        self.assertEqual(g_art["agent_id"], "agent.gaussian_splat.v1")
        self.assertEqual(
            g_art["catalog_entry"]["relative_dir"],
            "animazioni_3d/auto/motori/motore_v8",
        )

        n_art = neural_radiance_agent.run("cervello umano", persist=False)
        self.assertEqual(n_art["agent_id"], "agent.neural_radiance.v1")

        dp_art = depth_parallax_agent.run("medusa", persist=False)
        self.assertEqual(dp_art["agent_id"], "agent.depth_parallax.v1")

        dispatched = dispatch_visual_agent("Mostrami un diorama di Castel dell'Ovo", persist=False)
        self.assertEqual(dispatched["route"]["selected_engine"], "diorama")
        self.assertEqual(dispatched["artifact"]["agent_id"], "agent.diorama.v1")

    def test_visual_agents_feature_manifests_and_scanner(self):
        from agenti.team.scanner import scanner

        discovered = scanner.scan(force=True)
        expected_agents = (
            "particles",
            "diorama",
            "gaussian_splat",
            "neural_radiance",
            "depth_parallax",
        )
        for agent_id in expected_agents:
            self.assertIn(agent_id, discovered)
            record = discovered[agent_id]
            self.assertEqual(record.id, agent_id)
            self.assertTrue(Path(record.dir_path).exists())
            self.assertTrue((Path(record.dir_path) / "feature.json").exists())
            self.assertIsInstance(record.capabilities, list)
            self.assertGreater(len(record.capabilities), 0)
            self.assertIsInstance(record.routing, dict)

        import agenti

        self.assertEqual(agenti.creativita.particles.particle_agent.agent_id, "agent.particles.v1")
        self.assertEqual(
            agenti.creativita.gaussian_splat.gaussian_splat_agent.agent_id,
            "agent.gaussian_splat.v1",
        )


if __name__ == "__main__":
    unittest.main()



