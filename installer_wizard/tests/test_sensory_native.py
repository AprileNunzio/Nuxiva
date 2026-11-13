import array
import math
import random
import unittest

import native_core


def pcm(values):
    return array.array("f", values).tobytes()


def noise(seed, count):
    rng = random.Random(seed)
    return [rng.uniform(-0.3, 0.3) for _ in range(count)]


def voice(seed, dim=64):
    rng = random.Random(seed)
    return [rng.uniform(-0.5, 0.5) for _ in range(dim)]


def near(base, seed):
    rng = random.Random(seed)
    return [b + 0.3 * rng.uniform(-0.5, 0.5) for b in base]


def rms(values):
    return math.sqrt(sum(v * v for v in values) / max(1, len(values)))


@unittest.skipIf(native_core.symbol("RustEchoCanceller") is None, "modulo nativo assente")
class EchoCancellerTest(unittest.TestCase):

    def test_removes_playback_echo(self):
        far = noise(3, 16000 * 5)
        near_mic = [0.55 * (far[i - 120] if i >= 120 else 0.0) + 0.2 * (far[i - 200] if i >= 200 else 0.0)
                    for i in range(len(far))]
        aec = native_core.symbol("RustEchoCanceller")()
        out = []
        for start in range(0, len(far), 320):
            chunk = aec.process(pcm(near_mic[start:start + 320]), pcm(far[start:start + 320]))
            out.extend(array.array("f", chunk))
        tail = 16000 * 4
        self.assertLess(rms(out[tail:]), rms(near_mic[tail:]) * 0.1)
        self.assertTrue(aec.stats()[2])

    def test_rejects_bad_input(self):
        aec = native_core.symbol("RustEchoCanceller")()
        with self.assertRaises(ValueError):
            aec.process(pcm([0.0] * 4), pcm([0.0] * 5))
        with self.assertRaises(ValueError):
            aec.process(b"123", b"123")
        with self.assertRaises(ValueError):
            aec.process(pcm([0.0] * 20000), pcm([0.0] * 20000))


@unittest.skipIf(native_core.symbol("RustVoiceLock") is None, "modulo nativo assente")
class VoiceLockTest(unittest.TestCase):

    def setUp(self):
        self.owner = voice(1)
        self.rows = [near(self.owner, 100 + i) for i in range(8)]
        self.lock = native_core.symbol("RustVoiceLock")()

    def test_consent_is_required(self):
        with self.assertRaises(ValueError):
            self.lock.enroll("nunzio", self.rows, False)
        self.assertFalse(self.lock.enrolled())

    def test_only_the_owner_unlocks(self):
        self.lock.enroll("nunzio", self.rows, True)
        stranger = near(voice(2), 5)
        self.assertFalse(self.lock.observe(stranger, 0.0)[0])
        self.assertFalse(self.lock.observe(near(self.owner, 6), 1.0)[0])
        admit, unlocked, _, _ = self.lock.observe(near(self.owner, 7), 2.0)
        self.assertTrue(admit and unlocked)
        self.assertFalse(self.lock.observe(stranger, 3.0)[0])
        self.assertFalse(self.lock.unlocked(30.0))

    def test_sealed_voiceprint_round_trip(self):
        key = native_core.symbol("RustFernet").generate_key()
        self.lock.enroll("nunzio", self.rows, True)
        token = self.lock.seal(key, 1000)
        self.assertNotIn(b"nunzio", token)
        other = native_core.symbol("RustVoiceLock")()
        with self.assertRaises(ValueError):
            other.unseal(key, token, 1001, False)
        other.unseal(key, token, 1001, True)
        other.observe(near(self.owner, 6), 1.0)
        self.assertTrue(other.observe(near(self.owner, 7), 2.0)[0])
        self.lock.revoke()
        self.assertFalse(self.lock.enrolled())


@unittest.skipIf(native_core.symbol("RustIntentGate") is None, "modulo nativo assente")
class IntentGateTest(unittest.TestCase):

    def setUp(self):
        self.gate = native_core.symbol("RustIntentGate")()

    def test_commands_pass(self):
        for text in ("accendi la luce della cucina", "che tempo fa domani", "ricordami di comprare il pane"):
            with self.subTest(text=text):
                self.assertFalse(self.gate.judge(text)[2])

    def test_songs_chatter_and_noise_are_dropped(self):
        for text in ("la la la la la oh oh oh la la la", "mh mh", "thanks for watching",
                     "ieri a cena da Marco abbiamo mangiato benissimo e poi siamo usciti"):
            with self.subTest(text=text):
                self.assertTrue(self.gate.judge(text)[2])

    def test_name_overrides_drop(self):
        self.assertFalse(self.gate.judge("mh", True)[2])

    def test_oversized_text_is_rejected(self):
        with self.assertRaises(ValueError):
            self.gate.judge("a " * 20000)


@unittest.skipIf(native_core.symbol("RustVisualBuffer") is None, "modulo nativo assente")
class VisualBufferTest(unittest.TestCase):

    def frame(self, seed):
        return [1.0 if i % 7 == seed % 7 else 0.05 for i in range(32)]

    def test_no_consent_no_storage(self):
        buf = native_core.symbol("RustVisualBuffer")()
        self.assertEqual(buf.push("screen", "code", "main.rs", 0, self.frame(1)), "vision.no_consent")
        self.assertEqual(buf.len(), 0)
        self.assertFalse(buf.indicator(0)[0])

    def test_sensitive_apps_are_skipped(self):
        buf = native_core.symbol("RustVisualBuffer")(True)
        self.assertEqual(buf.push("screen", "1Password", "Vault", 10000, self.frame(1)), "vision.sensitive")
        self.assertEqual(buf.push("screen", "Firefox", "Home Banking", 10000, self.frame(1)), "vision.sensitive")
        self.assertEqual(buf.len(), 0)

    def test_query_context_and_revoke(self):
        buf = native_core.symbol("RustVisualBuffer")(True)
        self.assertEqual(buf.push("screen", "editor", "a", 0, self.frame(1)), "stored")
        self.assertEqual(buf.push("screen", "browser", "b", 3000, self.frame(2)), "stored")
        self.assertEqual(buf.query(self.frame(1), 4000, 2)[0][0], "editor")
        self.assertEqual(buf.current_app(4000), "browser")
        self.assertTrue(buf.indicator(4000)[0])
        self.assertIsNotNone(buf.context(4000))
        buf.set_policy(False, 2000, 300000, 256)
        self.assertEqual(buf.len(), 0)

    def test_bad_source_is_rejected(self):
        buf = native_core.symbol("RustVisualBuffer")(True)
        with self.assertRaises(ValueError):
            buf.push("mic", "a", "b", 0, self.frame(1))


if __name__ == "__main__":
    unittest.main()
