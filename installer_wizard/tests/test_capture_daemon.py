import random
import sys
import unittest
from pathlib import Path

import native_core
import numpy as np

VISION = Path(__file__).resolve().parents[1] / "agenti" / "percezione" / "vision"
if str(VISION) not in sys.path:
    sys.path.append(str(VISION))

import capture_cadence
from capture_cadence import PyCadence
from capture_daemon import CaptureDaemon, scene_ref
from capture_embed import TileEmbedder, VlmEmbedder, thumb

NATIVE = native_core.symbol("RustCadence") is not None and native_core.symbol("RustVisualBuffer") is not None


def picture(seed, size=64):
    rng = np.random.default_rng(seed)
    return rng.integers(0, 255, (size, size, 3), dtype=np.uint8)


def thumbs(count, seed=1):
    rng = random.Random(seed)
    base = bytes(rng.randrange(256) for _ in range(72))
    out = []
    for _ in range(count):
        if rng.random() < 0.5:
            out.append(base)
        else:
            out.append(bytes(rng.randrange(256) for _ in range(72)))
    return out


class Env(dict):
    def __call__(self, key, default):
        return self.get(key, default)


class Rig:
    def __init__(self, **env):
        self.now = 1000.0
        self.window = ("editor", "notes.txt")
        self.screen_image = picture(1)
        self.webcam_image = picture(2)
        self.screen_grabs = 0
        self.env = Env({"NUXIVA_CAPTURE_CONSENT": "1", "NUXIVA_CAPTURE_INTERVAL": "1000", "NUXIVA_CAPTURE_CEILING": "4000"})
        self.env.update(env)
        self.daemon = CaptureDaemon(self.env, lambda: self.webcam_image, TileEmbedder(), self.grab, lambda: self.window,
                                    lambda: self.now)

    def grab(self):
        self.screen_grabs += 1
        return self.screen_image

    def tick(self, seconds=1.0):
        self.now += seconds
        return self.daemon.step()


@unittest.skipUnless(NATIVE, "modulo nativo non installato")
class CaptureDaemonTest(unittest.TestCase):
    def test_nothing_is_captured_without_consent(self):
        rig = Rig(NUXIVA_CAPTURE_CONSENT="0")
        self.assertEqual(rig.tick(), 0)
        self.assertEqual(rig.screen_grabs, 0)
        self.assertEqual(rig.daemon.view()["frames"], 0)

    def test_consent_stores_both_sources(self):
        rig = Rig()
        self.assertEqual(rig.tick(), 2)
        view = rig.daemon.view()
        self.assertEqual(view["frames"], 2)
        self.assertTrue(view["active"])
        self.assertTrue(view["scene"].startswith("scene-"))

    def test_sensitive_window_is_not_even_grabbed(self):
        rig = Rig(NUXIVA_CAPTURE_SOURCES="screen")
        rig.window = ("firefox", "Home banking - accesso")
        self.assertEqual(rig.tick(), 0)
        self.assertEqual(rig.screen_grabs, 0)
        self.assertEqual(rig.daemon.reasons.get("sensitive"), 1)

    def test_unknown_window_fails_closed(self):
        rig = Rig(NUXIVA_CAPTURE_SOURCES="screen")
        rig.window = None
        self.assertEqual(rig.tick(), 0)
        self.assertEqual(rig.screen_grabs, 0)

    def test_window_switch_during_grab_discards_the_frame(self):
        rig = Rig(NUXIVA_CAPTURE_SOURCES="screen")
        answers = iter([("editor", "a"), ("1password", "vault")])
        rig.daemon._window = lambda: next(answers)
        self.assertEqual(rig.tick(), 0)
        self.assertEqual(rig.daemon.reasons.get("window_changed"), 1)

    def test_identical_frames_back_off_and_are_not_embedded_again(self):
        rig = Rig(NUXIVA_CAPTURE_SOURCES="webcam")
        self.assertEqual(rig.tick(), 1)
        for _ in range(8):
            rig.tick(5.0)
        self.assertEqual(rig.daemon.stats["embedded"], 1)
        self.assertGreaterEqual(rig.daemon.stats["unchanged"], 6)
        self.assertEqual(rig.daemon.cadence.interval_ms("webcam"), 4000)

    def test_change_embeds_again(self):
        rig = Rig(NUXIVA_CAPTURE_SOURCES="webcam")
        rig.tick()
        rig.webcam_image = picture(99)
        self.assertEqual(rig.tick(5.0), 1)

    def test_revoking_consent_wipes_the_buffer(self):
        rig = Rig()
        rig.tick()
        rig.env["NUXIVA_CAPTURE_CONSENT"] = "0"
        rig.tick()
        self.assertEqual(rig.daemon.view()["frames"], 0)

    def test_wipe_clears_frames_and_cadence(self):
        rig = Rig()
        rig.tick()
        rig.daemon.wipe()
        self.assertEqual(rig.daemon.view()["frames"], 0)
        self.assertEqual(rig.daemon.cadence.interval_ms("webcam"), 1000)

    def test_query_finds_the_stored_scene(self):
        rig = Rig(NUXIVA_CAPTURE_SOURCES="webcam")
        rig.tick()
        probe = TileEmbedder().embed(rig.webcam_image)
        hits = rig.daemon.query(probe, 3)
        self.assertEqual(hits[0]["source"], "webcam")
        self.assertGreater(hits[0]["score"], 0.99)

    def test_scene_ref_is_a_valid_swarm_ident(self):
        ref = scene_ref([0.1] * 40)
        self.assertRegex(ref, r"^scene-[0-9a-f]{20}$")
        self.assertIsNone(scene_ref(None))


class CadenceParityTest(unittest.TestCase):
    @unittest.skipUnless(NATIVE, "modulo nativo non installato")
    def test_python_and_rust_cadence_agree(self):
        native = native_core.symbol("RustCadence")(1000, 8000)
        python = PyCadence(1000, 8000)
        now = 0
        for index, frame in enumerate(thumbs(300)):
            now += 700 if index % 3 else 2500
            source = "screen" if index % 2 else "webcam"
            self.assertEqual(native.due(source, now), python.due(source, now))
            self.assertEqual(native.admit(source, frame, now), python.admit(source, frame, now))
            self.assertEqual(native.interval_ms(source), python.interval_ms(source))

    def test_python_fallback_rejects_bad_input(self):
        cadence = PyCadence()
        with self.assertRaises(ValueError):
            cadence.admit("screen", b"short", 0)
        with self.assertRaises(ValueError):
            cadence.admit("fax", bytes(72), 0)

    def test_factory_falls_back_without_native(self):
        original = capture_cadence.native_core.symbol
        capture_cadence.native_core.symbol = lambda name: None
        try:
            self.assertIsInstance(capture_cadence.make(1000, 4000), PyCadence)
        finally:
            capture_cadence.native_core.symbol = original


class EmbedderTest(unittest.TestCase):
    def test_vlm_refuses_remote_hosts(self):
        for url in ("http://example.com:11434", "https://127.0.0.1:11434", "http://10.0.0.5:11434"):
            with self.assertRaises(ValueError):
                VlmEmbedder(url, "v", "e")

    def test_vlm_requires_models(self):
        with self.assertRaises(ValueError):
            VlmEmbedder("http://127.0.0.1:11434", "", "e")

    def test_vlm_returns_none_when_server_is_down(self):
        embedder = VlmEmbedder("http://127.0.0.1:9", "v", "e", timeout=0.2)
        self.assertIsNone(embedder.embed(picture(3)))

    def test_tile_embedding_is_stable_and_sized(self):
        image = picture(4)
        first = TileEmbedder().embed(image)
        self.assertEqual(first, TileEmbedder().embed(image))
        self.assertEqual(len(first), 16 * 16 + 54)
        self.assertEqual(len(thumb(image)), 72)
