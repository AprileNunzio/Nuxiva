import unittest

from features.desktop.audience import Policy, Tracker


def face(confidence=0.9, liveness="unknown"):
    return {"person": "nunzio", "authorized": True, "confidence": confidence, "liveness": liveness, "near": True}


def scene(faces, voice_at=None, vision="ok"):
    voices = [] if voice_at is None else [{"person": "nunzio", "authorized": True, "score": 0.8, "at_ms": voice_at}]
    return {"vision": vision, "faces": faces, "voices": voices}


def opened():
    tracker = Tracker(Policy(), 0)
    tracker.step(scene([face()], 0), 0)
    assert tracker.step(scene([face()], 0), 1_500)["kind"] == "authorized"
    return tracker


class DoubtTests(unittest.TestCase):

    def test_a_brief_recognition_dip_keeps_the_widgets(self):
        tracker = opened()
        for now in range(12_000, 17_000, 1_000):
            self.assertEqual(tracker.step(scene([face(0.3)]), now)["kind"], "authorized", now)
        self.assertEqual(tracker.step(scene([face()]), 17_000)["kind"], "authorized")

    def test_a_lasting_doubt_still_closes(self):
        tracker = opened()
        tracker.step(scene([face(0.3)]), 12_000)
        self.assertEqual(tracker.step(scene([face(0.3)]), 18_000)["kind"], "uncertain")

    def test_a_live_face_keeps_its_hold_after_liveness_fades(self):
        tracker = Tracker(Policy(), 0)
        tracker.step(scene([face(liveness="live")]), 0)
        self.assertEqual(tracker.step(scene([face(liveness="live")]), 1_500)["kind"], "authorized")
        for now in range(2_000, 31_000, 1_000):
            self.assertEqual(tracker.step(scene([face()]), now)["kind"], "authorized", now)

    def test_the_speaker_own_weak_face_is_not_a_stranger(self):
        tracker = Tracker(Policy(), 0)
        tracker.step(scene([face(0.3)], 0), 0)
        self.assertEqual(tracker.step(scene([face(0.3)], 0), 1_500)["kind"], "authorized")

    def test_a_stranger_still_closes_at_once(self):
        tracker = opened()
        stranger = {"person": None, "authorized": False, "confidence": 0.0, "liveness": "unknown", "near": False}
        self.assertEqual(tracker.step(scene([stranger]), 2_000)["kind"], "guest_only")

    def test_a_camera_fault_still_closes_at_once(self):
        tracker = opened()
        self.assertEqual(tracker.step(scene([], vision="offline"), 2_000)["kind"], "uncertain")


if __name__ == "__main__":
    unittest.main()
