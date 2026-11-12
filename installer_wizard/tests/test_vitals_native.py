import random
import sys
import unittest
from pathlib import Path

import numpy as np

from features.people.vitals import consent as consent_module
from features.people.vitals.watch_engine import PyWatch

VISION = Path(__file__).resolve().parents[1] / "features" / "vision"
if str(VISION) not in sys.path:
    sys.path.insert(0, str(VISION))

import pulse

try:
    import nuxiva_native
except ImportError:
    nuxiva_native = None

NATIVE = nuxiva_native is not None and hasattr(nuxiva_native, "RustVitalWatch")


@unittest.skipUnless(NATIVE, "nuxiva_native senza vitals")
class VitalsParityTest(unittest.TestCase):

    def test_heart_rate_matches_python(self):
        rng = np.random.default_rng(3)
        for bpm in (55.0, 72.0, 110.0):
            ts = np.cumsum(rng.uniform(0.025, 0.04, 380)) + 1000.0
            wave = np.sin(2 * np.pi * bpm / 60 * ts)
            rgb = np.stack([120 + 0.3 * wave, 100 + 0.9 * wave, 80 + 0.2 * wave], axis=1) + rng.normal(0, 0.2, (ts.size, 3))
            native = nuxiva_native.vitals_heart_rate(ts.tolist(), rgb.tolist())
            python = pulse.py_heart_rate(ts, rgb)
            self.assertAlmostEqual(native[0], python[0], delta=0.05)
            self.assertAlmostEqual(native[1], python[1], delta=0.005)

    def test_breath_rate_matches_python(self):
        ts = np.arange(0, 30, 1 / 25) + 50.0
        shift = 0.02 * np.sin(2 * np.pi * 14 / 60 * ts)
        native = nuxiva_native.vitals_breath_rate(ts.tolist(), shift.tolist())
        python = pulse.py_breath_rate(ts, shift)
        self.assertAlmostEqual(native[0], python[0], delta=0.05)
        self.assertAlmostEqual(native[1], python[1], delta=0.005)

    def test_agreement_matches_python(self):
        rng = random.Random(9)
        for _ in range(300):
            seen = [None if rng.random() < 0.15 else rng.uniform(60, 75) for _ in range(3)]
            self.assertEqual(nuxiva_native.vitals_agreed(seen, 3, 6.0), pulse.py_agreed(seen, 6.0))

    def test_consent_matches_python(self):
        for flags in ((None, None, "owner", None), (False, None, "owner", True), (True, False, "family", None),
                      (True, None, "guest", None), (True, None, "service", True), (None, None, "", None)):
            self.assertEqual(nuxiva_native.vitals_camera_allowed(*flags), consent_module.py_decide(*flags))

    def test_watch_matches_python_on_a_random_day(self):
        rng = random.Random(21)
        native, python = nuxiva_native.RustVitalWatch(), PyWatch()
        names = ["anna", "luca", "sara", "dario", "elena", "Bad Slug"]
        now = 1000.0
        for _ in range(2500):
            now += rng.choice((0.5, 1.0, 1.0, 3.0, 20.0, 90.0))
            seen = []
            for slug in rng.sample(names, rng.randint(0, 5)):
                device = {"heart_rate": rng.choice((None, 62, 300))} if rng.random() < 0.08 else {}
                camera = {"heart_rate": rng.uniform(50, 120), "resp_rate": rng.choice((None, 14.4, 2))} if rng.random() < 0.2 else {}
                seen.append({"slug": slug, "device": device, "camera": camera})
            on = rng.random() > 0.05
            self.assertEqual(native.tick(seen, on, now), python.tick(seen, on, now))
        self.assertEqual(native.tracked(), python.tracked())

    def test_hostile_input_is_rejected(self):
        with self.assertRaises(ValueError):
            nuxiva_native.vitals_heart_rate([0.0] * 9000, [[1.0, 1.0, 1.0]] * 9000)
        watch = nuxiva_native.RustVitalWatch()
        shown, force = watch.tick([{"slug": "../etc"}, "x", {"slug": 5}, {"slug": "anna", "device": {"heart_rate": True}}], True, 1.0)
        self.assertEqual(shown, [])
        self.assertEqual(force, [("anna", 60.0)])


if __name__ == "__main__":
    unittest.main()
