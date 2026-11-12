from pathlib import Path
import tempfile
import unittest
from unittest import mock

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


class DedicatedParticlesDirectoryTest(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        self.store = ParticleStore(self.root)

    def test_dedicated_particles_pipeline(self):
        concept = extract_visual_concept("Come è fatta una medusa?")
        self.assertEqual(concept, "medusa")

        spec = synthesize_spec(concept)
        self.assertGreaterEqual(len(spec["parts"]), 7)

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
            self.assertIn("hotspots", entry)
            self.assertIn("xr", entry)
            self.assertIn("lod_stages", entry)

            cur = show.current()
            self.assertIsNotNone(cur)
            self.assertEqual(cur["concept"], "medusa")
            self.assertIn("hotspots", cur)
            show.clear()


if __name__ == "__main__":
    unittest.main()
