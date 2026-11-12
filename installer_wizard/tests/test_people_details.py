import sys
import tempfile
import unittest
from collections import deque
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import numpy as np

from agenti.people import details, people

VISION = Path(__file__).resolve().parents[1] / "agenti" / "percezione" / "vision"
if str(VISION) not in sys.path:
    sys.path.append(str(VISION))

import details as vision_details

NATIVE = details.look_class()


def seen(slug: str, at: float, glasses: float = 0.9, cigarette: float = 0.0, hair: str = "brown", state: str = "live") -> dict:
    return {"slug": slug, "known": True, "liveness": {"state": state},
            "details": {"samples": 8, "glasses": glasses, "beard": 0.1, "fringe": 0.1, "cigarette": cigarette, "hair": hair, "at": at}}


class CleanTest(unittest.TestCase):
    def test_bad_details_are_refused(self):
        self.assertIsNone(details.clean(None))
        self.assertIsNone(details.clean({"samples": 2, "glasses": 1}))
        self.assertIsNone(details.clean({"samples": "x"}))
        self.assertIsNone(details.clean({"samples": 8, "glasses": float("nan")}))
        sample = details.clean({"samples": 8, "glasses": 7, "beard": -1, "hair": "<b>"})
        self.assertEqual((sample["glasses"], sample["beard"], sample["hair"]), (1.0, 0.0, None))


class VisionDetailsTest(unittest.TestCase):
    def track(self):
        return SimpleNamespace(details=deque(maxlen=12), detail_at=0.0, detail_slug=None, aligned=np.full((112, 112, 3), 150, np.uint8),
                               live_state="live", facing=True, box=(100, 120, 160, 160))

    def test_samples_are_kept_per_person_and_skip_photos(self):
        frame = np.zeros((480, 640, 3), np.uint8)
        frame[60:140, 100:260] = (20, 50, 90)
        track = self.track()
        reading = {"glasses": 0.8, "beard": 0.2, "fringe": 0.1, "cigarette": 0.9}
        with mock.patch.object(vision_details.face_engine, "traits_of", side_effect=lambda _a: dict(reading)):
            for i in range(5):
                vision_details.observe(track, frame, "nunzio", 10.0 + i * 3)
            self.assertEqual(len(track.details), 5)
            view = vision_details.view(track)
            self.assertEqual((view["samples"], view["glasses"], view["cigarette"], view["hair"]), (5, 0.8, 1.0, "brown"))
            vision_details.observe(track, frame, "anna", 100.0)
            self.assertEqual(len(track.details), 1)
            track.live_state = "spoof"
            vision_details.observe(track, frame, "anna", 200.0)
            self.assertEqual(len(track.details), 1)
        self.assertIsNone(vision_details.view(track))


@unittest.skipIf(NATIVE is None, "modulo Rust nuxiva_native non installato")
class LearnerTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        self.patch = mock.patch.object(people, "PEOPLE_DIR", self.dir)
        self.patch.start()
        people.ensure("nunzio", "Nunzio")
        self.learner = details.DetailLearner()

    def tearDown(self):
        self.patch.stop()
        self.tmp.cleanup()

    def feed(self, start: int, count: int, **kw) -> list:
        out = []
        for i in range(start, start + count):
            out += self.learner.ingest([seen("nunzio", float(i), **kw)], now=1000.0 + i * 6)
        return out

    def test_glasses_and_smoking_are_learned_and_stored_encrypted(self):
        events = self.feed(0, 20)
        self.assertEqual([(e["kind"], e["value"]) for e in events if e["kind"] == "glasses"], [("glasses", "on")])
        self.feed(20, 2, cigarette=0.8)
        self.feed(200, 2, cigarette=0.8)
        view = self.learner.view("nunzio")
        self.assertTrue(view["summary"]["glasses"] and view["summary"]["smoker"])
        self.assertEqual(view["summary"]["hair"], "brown")
        public = (self.dir / "nunzio.json").read_text(encoding="utf-8")
        self.assertNotIn("face_traits", public)
        self.assertNotIn("glasses", public)
        self.assertIn("face_traits", people.load("nunzio"))

    def test_wrong_detail_is_forgotten(self):
        self.feed(0, 20)
        row = next(e for e in self.learner.view("nunzio")["events"] if e["kind"] == "glasses")
        self.assertEqual(self.learner.feedback("nunzio", row["id"], "wrong")["status"], "rejected")
        view = self.learner.view("nunzio")
        self.assertFalse(view["summary"]["glasses"])
        self.assertIsNone(self.learner.feedback("nunzio", "0000000000", "ok"))
        with self.assertRaises(ValueError):
            self.learner.feedback("nunzio", row["id"], "maybe")

    def test_no_consent_spoof_and_repeats_teach_nothing(self):
        profile = people.load("nunzio")
        profile["consent"] = False
        people.save(profile)
        self.assertEqual(self.feed(0, 20), [])
        self.learner = details.DetailLearner()
        profile["consent"] = True
        people.save(profile)
        self.assertEqual(self.feed(0, 20, state="spoof"), [])
        for i in range(20):
            self.learner.ingest([seen("nunzio", 5.0)], now=2000.0 + i * 6)
        self.assertEqual(self.learner.view("nunzio")["summary"]["observations"], 1)

    def test_a_broken_state_starts_again(self):
        profile = people.load("nunzio")
        profile["face_traits"] = {"state": "{bad", "events": ["x", {"id": "abc"}]}
        people.save(profile)
        view = self.learner.view("nunzio")
        self.assertEqual(view["summary"]["observations"], 0)
        self.assertEqual(len(view["events"]), 1)
        self.assertTrue(self.feed(0, 20))


if __name__ == "__main__":
    unittest.main()
