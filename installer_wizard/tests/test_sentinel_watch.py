import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import numpy as np

from agenti.sentinel import memory_people, observe, vault
from agenti.sentinel.memory import Memory
from agenti.sentinel.watch import Watcher

VISION = Path(__file__).resolve().parents[1] / "agenti" / "percezione" / "vision"
if str(VISION) not in sys.path:
    sys.path.insert(0, str(VISION))

import bodies  # noqa: E402

T0 = 1_793_900_000.0


def _native():
    try:
        import nuxiva_native
    except ImportError:
        return None
    return getattr(nuxiva_native, "RustSightingAssembler", None)


def frame() -> np.ndarray:
    img = np.full((400, 600, 3), 90, dtype=np.uint8)
    img[60:180, 100:200] = (0, 0, 220)
    img[200:330, 100:200] = (200, 60, 0)
    img[120:300, 350:560] = (245, 245, 245)
    return img


class BodiesTests(unittest.TestCase):

    def test_person_colours_items_and_vehicle(self):
        found = [{"label": "persona", "score": 0.9, "box": [100, 30, 100, 330]},
                 {"label": "borsa", "score": 0.6, "box": [150, 200, 40, 60]},
                 {"label": "automobile", "score": 0.8, "box": [340, 110, 230, 200]},
                 {"label": "sedia", "score": 0.9, "box": [0, 0, 20, 20]}]
        out = bodies.describe(frame(), found)
        person = next(b for b in out if b["class"] == "person")
        self.assertEqual(person["look"]["upper"], "red")
        self.assertEqual(person["look"]["lower"], "blue")
        self.assertEqual(person["look"]["carrying"], ["bag"])
        self.assertTrue(all(0.0 <= v <= 1.0 for v in person["box"]))
        car = next(b for b in out if b["class"] == "vehicle")
        self.assertEqual(car["vehicle"], {"kind": "car", "color": "white"})
        self.assertEqual(len(out), 2)


class ObserveTests(unittest.TestCase):

    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        patcher = mock.patch.object(vault, "STATE_DIR", self.root)
        patcher.start()
        self.addCleanup(patcher.stop)

    def result(self):
        return {"bodies": [
            {"class": "person", "box": [0.1, 0.1, 0.2, 0.8], "score": 0.9,
             "look": {"upper": "red", "lower": "blue", "carrying": ["bag", "bomb"], "hi_vis": True}},
            {"class": "vehicle", "box": [0.5, 0.3, 0.4, 0.4], "score": 0.7, "vehicle": {"kind": "spaceship"}},
            {"class": "person", "box": [2, 0, 0, 0], "score": 0.5}]}

    def test_rows_are_cleaned(self):
        rows = observe.observations({"id": "Cam 1/Ingresso", "room": "Ingresso"}, self.result(), 1000)
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row["camera"], "cam-1-ingresso")
        self.assertEqual(row["zone"], "ingresso")
        self.assertEqual(row["look"]["carrying"], ["bag"])
        self.assertNotIn("who", row)

    def test_face_inside_head_area_names_the_body(self):
        profile = {"slug": "nunzio", "name": "Nunzio", "consent": True}
        with mock.patch.object(memory_people, "_profile", return_value=profile):
            rows = observe.observations({"id": "main"}, self.result(), 1000, [(0.2, 0.2, "nunzio")])
        self.assertEqual(rows[0]["who"]["type"], "person")
        self.assertEqual(rows[0]["look"]["upper"], "red")

    def test_no_consent_drops_the_look(self):
        profile = {"slug": "anna", "name": "Anna", "consent": False}
        with mock.patch.object(memory_people, "_profile", return_value=profile):
            rows = observe.observations({"id": "main"}, self.result(), 1000, [(0.2, 0.2, "anna")])
        self.assertEqual(rows[0]["look"], {})

    def test_two_faces_in_one_body_stay_unknown(self):
        with mock.patch.object(memory_people, "_profile", return_value={"slug": "x", "name": "X"}):
            rows = observe.observations({"id": "main"}, self.result(), 1000, [(0.2, 0.2, "a"), (0.25, 0.3, "b")])
        self.assertNotIn("who", rows[0])


class Clock:
    def __init__(self, t: float) -> None:
        self.t = t

    def __call__(self) -> float:
        return self.t


@unittest.skipIf(_native() is None, "nuxiva_native.RustSightingAssembler not built")
class WatcherTests(unittest.TestCase):

    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        patcher = mock.patch.object(vault, "STATE_DIR", self.root)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.clock = Clock(T0)
        self.memory = Memory(clock=self.clock)
        self.memory.swept_at = T0
        patcher = mock.patch("agenti.sentinel.watch.memory", self.memory)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_courier_is_remembered_and_found(self):
        watcher = Watcher(clock=self.clock)
        result = {"bodies": [{"class": "person", "box": [0.1, 0.1, 0.2, 0.8], "score": 0.9,
                              "look": {"upper": "yellow", "hi_vis": True, "carrying": ["bag"]}},
                             {"class": "vehicle", "box": [0.5, 0.3, 0.4, 0.4], "score": 0.8,
                              "vehicle": {"kind": "van", "color": "white"}}]}
        for step in range(3):
            self.clock.t = T0 + step * 5
            rows = observe.observations({"id": "ingresso"}, result, int(self.clock.t * 1000))
            self.assertEqual(watcher.feed(rows), [])
        self.clock.t = T0 + 60
        done = watcher.feed([])
        self.assertEqual(len(done), 2)
        self.assertEqual(watcher.store(done), 2)
        page = self.memory.search({"from_ms": int((T0 - 60) * 1000), "to_ms": int((T0 + 60) * 1000),
                                   "hi_vis": True})
        self.assertEqual(len(page["sightings"]), 1)
        import nuxiva_native
        episodes = json.loads(nuxiva_native.memory_episodes(json.dumps(done)))
        self.assertIn("delivery", [e["kind"] for e in episodes])


if __name__ == "__main__":
    unittest.main()
