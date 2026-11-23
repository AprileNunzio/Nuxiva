import math
import unittest

import numpy as np

from ui.hologram import palette
from ui.hologram.motion import REST_OPACITY, TICKS, Motion, sanitize_level
from ui.hologram.scene import Scene

SIZE = 96


def frame(scene: Scene, motion: Motion) -> np.ndarray:
    return np.frombuffer(scene.render(motion), dtype=np.uint8).reshape(SIZE, SIZE, 4)


def settle(state: str, level: float = 0.0, steps: int = 45, hovered: bool = False) -> Motion:
    motion = Motion()
    for _ in range(steps):
        motion.step(state, level, hovered, 1 / 30)
    return motion


class SceneTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.scene = Scene(SIZE)

    def test_frame_is_premultiplied_bgra_with_clear_corners(self):
        for state in palette.TONES:
            pixels = frame(self.scene, settle(state, 0.05))
            self.assertTrue((pixels[..., :3] <= pixels[..., 3:4]).all(), state)
            for y, x in ((0, 0), (0, -1), (-1, 0), (-1, -1)):
                self.assertEqual(pixels[y, x, 3], 0, state)
            self.assertEqual(pixels[SIZE // 2, SIZE // 2, 3] > 200, True, state)

    def test_voice_makes_the_hologram_brighter(self):
        quiet = frame(self.scene, settle("listening", 0.0)).astype(np.int64).sum()
        loud = frame(self.scene, settle("listening", 0.08)).astype(np.int64).sum()
        self.assertGreater(loud, quiet)

    def test_states_are_visually_distinct(self):
        idle = frame(self.scene, settle("idle"))
        thinking = frame(self.scene, settle("thinking"))
        self.assertGreater(np.abs(idle.astype(np.int64) - thinking).sum(), 0)

    def test_tiny_sizes_are_rejected(self):
        with self.assertRaises(ValueError):
            Scene(8)


class MotionTest(unittest.TestCase):
    def test_levels_are_sanitized(self):
        for bad in (float("nan"), float("inf"), -1.0, "x", None):
            self.assertEqual(sanitize_level(bad), 0.0)
        self.assertEqual(sanitize_level(0.25), 0.25)

    def test_unknown_state_falls_back_to_idle(self):
        motion = settle("<script>")
        self.assertEqual(motion.state, palette.DEFAULT)

    def test_rest_is_translucent_and_hover_is_opaque(self):
        self.assertAlmostEqual(settle("idle", steps=120).opacity, REST_OPACITY, places=2)
        self.assertAlmostEqual(settle("idle", steps=120, hovered=True).opacity, 1.0, places=2)

    def test_ambient_flow_stays_alive_when_idle(self):
        motion = settle("idle", steps=120)
        self.assertGreater(motion.reveal, 0.2)
        self.assertLess(motion.reveal, 0.5)

    def test_spectrum_follows_voice_and_stays_bounded(self):
        loud = settle("speaking", 0.1)
        self.assertEqual(loud.ticks.shape, (TICKS,))
        self.assertTrue(((loud.ticks >= 0.0) & (loud.ticks <= 1.0)).all())
        self.assertGreater(loud.ticks.mean(), settle("speaking", 0.0).ticks.mean())

    def test_large_frame_gaps_do_not_explode(self):
        motion = Motion()
        motion.step("speaking", 0.1, False, 30.0)
        self.assertTrue(math.isfinite(motion.phase))
        self.assertTrue(np.isfinite(motion.color).all())
