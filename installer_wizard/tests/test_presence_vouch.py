import json
import random
import unittest

from features.desktop import presence_bridge
from features.desktop.audience import Policy, Tracker

WEBCAM = {"person": "nunzio", "authorized": True, "confidence": 0.9, "liveness": "unknown", "near": True}


def webcam(voice_at=None, liveness="unknown", vision="ok", faces=None):
    voices = [] if voice_at is None else [{"person": "nunzio", "authorized": True, "score": 0.8, "at_ms": voice_at}]
    return {"vision": vision, "faces": [{**WEBCAM, "liveness": liveness}] if faces is None else faces, "voices": voices}


def opened(policy=Policy()):
    tracker = Tracker(policy, 0)
    tracker.step(webcam(0), 0)
    assert tracker.step(webcam(0), 1_500)["kind"] == "authorized"
    return tracker


class VouchTests(unittest.TestCase):

    def test_a_spoken_owner_stays_authorized_while_the_face_stays_in_view(self):
        tracker = opened()
        for now in range(2_000, 30_000, 1_000):
            self.assertEqual(tracker.step(webcam(), now)["kind"], "authorized", now)

    def test_the_hold_ends_with_the_configured_voice_time(self):
        tracker = opened()
        for now in range(2_000, 36_000, 1_000):
            self.assertEqual(tracker.step(webcam(), now)["kind"], "authorized", now)
        self.assertEqual(tracker.step(webcam(), 36_000)["kind"], "uncertain")

    def test_speaking_again_renews_the_hold(self):
        tracker = opened()
        for now in range(2_000, 51_000, 1_000):
            spoken = 25_000 if now == 25_000 else None
            self.assertEqual(tracker.step(webcam(spoken), now)["kind"], "authorized", now)

    def test_losing_the_face_breaks_the_hold(self):
        tracker = opened()
        tracker.step(webcam(faces=[]), 2_000)
        tracker.step(webcam(faces=[]), 6_000)
        tracker.step(webcam(), 12_000)
        self.assertEqual(tracker.step(webcam(), 18_000)["kind"], "uncertain")

    def test_a_spoof_cancels_the_hold(self):
        tracker = opened()
        tracker.step(webcam(liveness="spoof"), 2_000)
        self.assertEqual(tracker.step(webcam(), 2_500)["kind"], "uncertain")

    def test_a_camera_fault_cancels_the_hold(self):
        tracker = opened()
        tracker.step(webcam(vision="offline"), 2_000)
        self.assertEqual(tracker.step(webcam(), 2_500)["kind"], "uncertain")

    def test_a_photo_never_spoken_for_opens_nothing(self):
        tracker = Tracker(Policy(), 0)
        for now in range(0, 21_000, 1_000):
            self.assertNotEqual(tracker.step(webcam(), now)["kind"], "authorized")

    def test_liveness_turned_off_needs_no_hold(self):
        tracker = Tracker(Policy(require_liveness=False), 0)
        tracker.step(webcam(), 0)
        self.assertEqual(tracker.step(webcam(), 1_500)["kind"], "authorized")

    def test_the_vouch_memory_is_bounded(self):
        tracker = Tracker(Policy(require_liveness=True), 0)
        faces = [{**WEBCAM, "person": f"p{i}"} for i in range(32)]
        voices = [{"person": f"p{i}", "authorized": True, "score": 0.9, "at_ms": 0} for i in range(64)]
        for now in (0, 500, 1_000):
            tracker.step({"vision": "ok", "faces": faces, "voices": voices}, now)
        self.assertLessEqual(len(tracker.vouched), 32)


def _native():
    try:
        import nuxiva_native
    except ImportError:
        return None
    return getattr(nuxiva_native, "RustPresenceTracker", None)


@unittest.skipUnless(_native(), "motore nativo non installato")
class VouchParityTests(unittest.TestCase):

    def test_rust_and_python_agree_on_webcam_sequences(self):
        rng = random.Random(36)
        pool = [WEBCAM, {**WEBCAM, "liveness": "live"}, {**WEBCAM, "liveness": "spoof"}, {**WEBCAM, "confidence": 0.3},
                {**WEBCAM, "person": "anna"}]
        for _ in range(40):
            policy = Policy(voice_hold_ms=rng.choice((0, 15_000, 30_000, 120_000)))
            native = presence_bridge.NativeTracker(_native()(json.dumps(policy.as_dict()), 0))
            python, now = Tracker(policy, 0), 0
            for _ in range(80):
                now += rng.choice((200, 700, 1_000, 2_500, 5_000))
                vision = rng.choice(("ok",) * 8 + ("offline",))
                faces = rng.sample(pool, rng.randint(0, 2))
                voices = [{"person": rng.choice(("nunzio", "anna")), "authorized": True, "score": 0.8,
                           "at_ms": max(0, now - rng.randint(0, 12_000))}] if rng.random() < 0.15 else []
                signals = {"vision": vision, "faces": faces, "voices": voices}
                self.assertEqual(native.step(signals, now), python.step(signals, now))


if __name__ == "__main__":
    unittest.main()
