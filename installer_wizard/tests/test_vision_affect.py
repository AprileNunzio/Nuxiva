import sys
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "features" / "vision"))

import affect


def make_face(smile: float = 0.0) -> np.ndarray:
    face = np.zeros(15, dtype=np.float32)
    face[4:14] = [140, 120, 200, 120, 170, 160, 148 - smile * 6, 195 - smile * 4, 192 + smile * 6, 195 - smile * 4]
    return face


def make_frame(texture: bool) -> np.ndarray:
    frame = np.full((300, 340), 120, dtype=np.uint8)
    if texture:
        frame[85:110, 150:190:3] = 40
    return frame


class AffectTest(unittest.TestCase):

    def test_smile_widens_the_mouth(self):
        calm = affect.mouth_geometry(make_face(0.0))
        smile = affect.mouth_geometry(make_face(1.0))
        self.assertGreater(smile["width"], calm["width"])
        self.assertLess(smile["drop"], calm["drop"])

    def test_tiny_faces_are_ignored(self):
        face = make_face()
        face[4:8] = [100, 100, 108, 100]
        self.assertIsNone(affect.mouth_geometry(face))

    def test_vertical_furrows_raise_glabella_energy(self):
        flat = affect.glabella_energy(make_frame(False), make_face())
        furrowed = affect.glabella_energy(make_frame(True), make_face())
        self.assertGreater(furrowed, flat)

    def test_face_near_the_border_is_skipped(self):
        face = make_face()
        face[4:6] = [2, 2]
        self.assertIsNone(affect.glabella_energy(make_frame(False), face))

    def test_meter_is_rate_limited_and_reports_mimic_after_warmup(self):
        meter = affect.AffectMeter()
        frame = make_frame(False)
        first = meter.update(frame, make_face(), 10.0)
        self.assertIsNotNone(first)
        self.assertIs(meter.update(frame, make_face(), 10.1), first)
        out = None
        for i in range(1, 10):
            out = meter.update(frame, make_face(i % 2), 10.0 + i)
        self.assertIsNotNone(out["mimic"])
        self.assertGreater(out["mimic"], 0)


if __name__ == "__main__":
    unittest.main()
