import math
import unittest
from features.vision.gait import GaitCore


class TestGait(unittest.TestCase):

    def setUp(self):
        self.gait = GaitCore(prefer_native=False)

    def _sample_observations(self, count=20, dur_ms=2000):
        dt = dur_ms / count
        obs = []
        for i in range(count):
            t = int(i * dt)
            prog = i / count
            x = 100.0 + prog * 150.0 + math.sin(prog * 12.56) * 5.0
            y = 150.0 + math.cos(prog * 12.56) * 8.0
            w = 40.0
            h = 170.0
            obs.append({"timestamp_ms": t, "x": x, "y": y, "width": w, "height": h})
        return obs

    def test_extract_success(self):
        obs = self._sample_observations()
        sig = self.gait.extract(obs)
        self.assertEqual(sig["samples"], 20)
        self.assertEqual(len(sig["features"]), 16)
        self.assertGreater(sig["confidence"], 0.3)

    def test_extract_insufficient_samples(self):
        obs = self._sample_observations(count=3)
        with self.assertRaises(ValueError):
            self.gait.extract(obs)

    def test_extract_insufficient_duration(self):
        obs = self._sample_observations(count=10, dur_ms=200)
        with self.assertRaises(ValueError):
            self.gait.extract(obs)

    def test_evaluate_match_high_similarity(self):
        cand = {"features": [0.5] * 16, "samples": 10, "confidence": 0.8}
        ref = {"features": [0.5] * 16, "samples": 10, "confidence": 0.8}
        res = self.gait.evaluate(cand, ref, ref_id="s-1", ref_ts_ms=1700000000000)
        self.assertAlmostEqual(res["similarity"], 1.0, places=3)
        self.assertTrue(res["probable_match"])
        self.assertFalse(res["is_biometric_conclusive"])
        self.assertIn("probabilmente", res["narrative_it"])

    def test_evaluate_match_low_similarity(self):
        cand = {"features": [0.1] * 16, "samples": 10, "confidence": 0.8}
        ref = {"features": [-0.9] * 16, "samples": 10, "confidence": 0.8}
        res = self.gait.evaluate(cand, ref)
        self.assertFalse(res["probable_match"])
        self.assertFalse(res["is_biometric_conclusive"])
        self.assertIn("non corrispondente", res["narrative_it"])

    def test_find_best(self):
        cand = {"features": [0.5] * 16, "samples": 10, "confidence": 0.8}
        refs = [
            {"id": "r-1", "timestamp_ms": 1000, "signature": {"features": [0.1] * 16, "confidence": 0.8}},
            {"id": "r-2", "timestamp_ms": 2000, "signature": {"features": [0.49] * 16, "confidence": 0.8}},
        ]
        best = self.gait.find_best(cand, refs)
        self.assertIsNotNone(best)
        self.assertEqual(best["reference_id"], "r-2")
        self.assertTrue(best["probable_match"])

    def test_aggregate(self):
        s1 = {"features": [0.2] * 16, "samples": 5, "confidence": 0.6}
        s2 = {"features": [0.4] * 16, "samples": 5, "confidence": 0.8}
        agg = self.gait.aggregate([s1, s2])
        self.assertEqual(agg["samples"], 10)
        self.assertAlmostEqual(agg["features"][0], 0.3, places=5)
        self.assertAlmostEqual(agg["confidence"], 0.7, places=5)


if __name__ == "__main__":
    unittest.main()
