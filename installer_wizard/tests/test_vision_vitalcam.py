import sys
import unittest
from pathlib import Path
from unittest import mock

import cv2
import numpy as np

VISION = Path(__file__).resolve().parents[1] / "agenti" / "percezione" / "vision"
if str(VISION) not in sys.path:
    sys.path.insert(0, str(VISION))

import pulse
import vitalcam

FPS = 30.0
BOX = (120, 60, 100, 120)
FACE = np.array([*BOX, 145, 110, 195, 110, 170, 140, 150, 160, 190, 160, 0.99], dtype=np.float32)


TEXTURE = cv2.GaussianBlur(np.random.default_rng(5).integers(0, 255, (300, 360)).astype(np.float32), (0, 0), 3.0)


def frame_at(t: float, bpm: float = 72.0, rpm: float = 15.0) -> np.ndarray:
    frame = np.full((480, 360, 3), 60, dtype=np.uint8)
    shift = 3.0 * np.sin(2 * np.pi * rpm / 60 * t)
    chest = cv2.warpAffine(TEXTURE, np.float32([[1, 0, 0], [0, 1, shift]]), (360, 300), borderMode=cv2.BORDER_REFLECT)
    frame[180:480] = np.clip(chest, 0, 255).astype(np.uint8)[:, :, None]
    beat = 1.0 + 0.01 * np.sin(2 * np.pi * bpm / 60 * t)
    skin = np.clip(np.array([90.0, 120.0, 170.0]) * np.array([1.0, beat, 1.0 + (beat - 1) * 0.4]), 0, 255)
    frame[60:180, 120:220] = skin.astype(np.uint8)
    return frame


class Track:
    def __init__(self, slug: str) -> None:
        self.id = 7
        self.slug = slug
        self.face = FACE
        self.box = BOX
        self.facing = True
        self.last_seen = 0.0

    def identity(self):
        return self.slug, self.slug, 0.9


class PulseMathTest(unittest.TestCase):

    def test_heart_rate_found_in_noisy_color_trace(self):
        rng = np.random.default_rng(3)
        ts = np.cumsum(rng.uniform(0.8, 1.2, 360) / 28)
        wave = np.sin(2 * np.pi * 66 / 60 * ts)[:, None] * np.array([0.33, 0.77, 0.53])
        rgb = np.array([150.0, 110.0, 90.0]) * (1 + 0.004 * wave) + rng.normal(0, 0.1, (ts.size, 3))
        bpm, quality = pulse.heart_rate(ts, rgb)
        self.assertAlmostEqual(bpm, 66, delta=2)
        self.assertGreater(quality, 0.3)

    def test_breath_rate_found_in_chest_shift(self):
        ts = np.arange(0, 30, 1 / 30)
        rpm, quality = pulse.breath_rate(ts, 0.02 * np.sin(2 * np.pi * 12 / 60 * ts))
        self.assertAlmostEqual(rpm, 12, delta=1)
        self.assertGreater(quality, 0.6)

    def test_short_or_broken_traces_give_nothing(self):
        self.assertEqual(pulse.heart_rate(np.arange(5.0), np.ones((5, 3))), (0.0, 0.0))
        self.assertEqual(pulse.breath_rate(np.arange(0, 5, 0.1), np.zeros(50)), (0.0, 0.0))
        ts = np.arange(0, 10, 1 / 30)
        self.assertEqual(pulse.heart_rate(ts, np.zeros((ts.size, 3))), (0.0, 0.0))

    def test_face_regions_need_a_large_enough_face(self):
        frame = frame_at(0.0)
        self.assertEqual(vitalcam.face_rgb(frame, FACE).shape, (3,))
        tiny = FACE.copy()
        tiny[6] = tiny[4] + 5
        self.assertIsNone(vitalcam.face_rgb(frame, tiny))
        self.assertIsNone(vitalcam.face_rgb(frame[:, :, 0], FACE))


class MeterTest(unittest.TestCase):

    def test_meter_measures_pulse_and_breath_from_frames(self):
        meter = vitalcam.PersonMeter()
        reading = None
        for i in range(int(40 * FPS)):
            t = i / FPS
            meter.sample(frame_at(t), FACE, BOX, t)
            if i % 15 == 0:
                reading = meter.estimate(t)
        self.assertAlmostEqual(reading["heart_rate"], 72, delta=3)
        self.assertAlmostEqual(reading["resp_rate"], 15, delta=2)
        self.assertEqual(reading["progress"], 1.0)

    def test_big_head_movement_restarts_the_measure(self):
        meter = vitalcam.PersonMeter()
        for i in range(60):
            meter.sample(frame_at(i / FPS), FACE, BOX, i / FPS)
        moved = FACE.copy()
        moved[[0, 4, 6, 8, 10, 12]] += 80
        meter.sample(frame_at(2.1), moved, (200, 60, 100, 120), 2.1)
        self.assertEqual(len(meter.colors), 1)
        self.assertEqual(len(meter.chest_rows), 0)


class VitalCamTest(unittest.TestCase):

    def test_only_valid_requested_people_are_measured(self):
        cam = vitalcam.VitalCam()
        with mock.patch.object(vitalcam.selection, "rppg_enabled", return_value=True):
            cam.want("anna,../etc,BAD,luca", now=100.0)
            self.assertEqual(cam.active(101.0), {"anna", "luca"})
            self.assertEqual(cam.active(105.0), set())
            cam.want("anna", now=200.0)
            track = Track("anna")
            track.last_seen = 200.0
            self.assertTrue(cam.busy([track], 200.1))
            cam.sample(frame_at(0.0), [track], 200.1)
            self.assertEqual(cam.cost()["frames"], 1)
            self.assertIsNotNone(cam.reading(track, 200.2))
            self.assertFalse(cam.busy([Track("piero")], 200.2))

    def test_setting_off_stops_everything(self):
        cam = vitalcam.VitalCam()
        cam.want("anna", now=100.0)
        with mock.patch.object(vitalcam.selection, "rppg_enabled", return_value=False):
            track = Track("anna")
            track.last_seen = 100.0
            self.assertFalse(cam.busy([track], 100.1))
            cam.sample(frame_at(0.0), [track], 100.1)
            self.assertEqual(cam.cost()["frames"], 0)
            self.assertIsNone(cam.reading(track, 100.2))


if __name__ == "__main__":
    unittest.main()
