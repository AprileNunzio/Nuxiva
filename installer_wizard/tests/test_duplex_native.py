import json
import unittest

from agenti.ear import duplex

try:
    import nuxiva_native
except ImportError:
    nuxiva_native = None

NATIVE = nuxiva_native is not None and hasattr(nuxiva_native, "RustDuplex")


class Common:
    def make(self):
        raise NotImplementedError

    def speaking(self):
        s = self.make()
        s.trigger("voice_start", 1)
        s.trigger("voice_end", 2)
        return s, s.begin_reply(3)

    def test_walk_through_the_states(self):
        s, epoch = self.speaking()
        self.assertEqual(epoch, 1)
        self.assertEqual(json.loads(s.snapshot())["state"], "speaking")
        self.assertEqual(json.loads(s.finish(epoch, 9)), "idle")

    def test_illegal_transition_keeps_state(self):
        s = self.make()
        with self.assertRaisesRegex(ValueError, "duplex.transition"):
            s.trigger("voice_end", 1)
        with self.assertRaisesRegex(ValueError, "duplex.invalid"):
            s.trigger("nonsense", 1)
        self.assertEqual(json.loads(s.snapshot())["state"], "idle")

    def test_cut_cancels_flags_and_marks_stale(self):
        s, epoch = self.speaking()
        flag = s.bind(epoch)
        s.mark_spoken(epoch, 12)
        report = json.loads(s.cut(epoch, 40))
        self.assertEqual((report["cancelled"], report["state"]), (1, "interrupted"))
        self.assertEqual(report["interruption"]["spoken_chars"], 12)
        self.assertTrue(flag.is_cancelled())
        self.assertFalse(s.is_live(epoch))
        for call in (lambda: s.next_seq(epoch), lambda: s.admit(epoch, 1, 41), lambda: s.bind(epoch)):
            with self.assertRaisesRegex(ValueError, "duplex.stale"):
                call()

    def test_interrupt_trigger_routes_through_cut(self):
        s, epoch = self.speaking()
        flag = s.bind(epoch)
        s.trigger("interrupt", 9)
        self.assertTrue(flag.is_cancelled())
        self.assertEqual(json.loads(s.snapshot())["state"], "interrupted")

    def test_new_generation_survives_old_cut(self):
        s, first = self.speaking()
        s.cut(first, 10)
        s.trigger("resume", 11)
        s.trigger("voice_end", 12)
        second = s.begin_reply(13)
        flag = s.bind(second)
        self.assertEqual(json.loads(s.cut(first, 14))["cancelled"], 0)
        self.assertFalse(flag.is_cancelled())
        self.assertTrue(s.is_live(second))

    def test_sequences_rate_and_timeouts(self):
        s = self.make()
        s.admit(0, 1, 0)
        with self.assertRaisesRegex(ValueError, "duplex.sequence"):
            s.admit(0, 1, 0)
        ok = 0
        for seq in range(2, 1000):
            try:
                s.admit(0, seq, 0)
                ok += 1
            except ValueError as exc:
                self.assertEqual(str(exc), "duplex.rate_limited")
        self.assertEqual(ok, 198)
        s2, epoch = self.speaking()
        flag = s2.bind(epoch)
        self.assertIsNone(s2.tick(3 + 299_999))
        self.assertEqual(json.loads(s2.tick(3 + 300_000)), "idle")
        self.assertTrue(flag.is_cancelled())

    def test_reset_from_any_state(self):
        s, epoch = self.speaking()
        flag = s.bind(epoch)
        s.trigger("reset", 4)
        self.assertTrue(flag.is_cancelled())
        self.assertEqual(json.loads(s.snapshot())["bound_tokens"], 0)


class PythonFallbackTest(Common, unittest.TestCase):
    def make(self):
        return duplex.PyDuplex("", 0)


@unittest.skipUnless(NATIVE, "modulo nativo non installato")
class NativeTest(Common, unittest.TestCase):
    def make(self):
        return nuxiva_native.RustDuplex("", 0)

    def test_frames_are_validated_natively(self):
        s = self.make()
        self.assertEqual(json.loads(s.parse_control('{"type":"cut","gen":3}')), {"type": "cut", "gen": 3})
        for bad in ('{"type":"cut","gen":1,"x":1}', "nope", '{"type":"hello","version":9}'):
            with self.assertRaises(ValueError):
                s.parse_control(bad)
        frame = bytes([1]) + (7).to_bytes(4, "big") + (42).to_bytes(4, "big") + b"\x01\x02"
        self.assertEqual(s.decode_audio(frame), (7, 42, 2))
        with self.assertRaises(ValueError):
            s.decode_audio(b"\x02" + frame[1:])

    def test_native_and_fallback_agree_on_a_scripted_session(self):
        script = [("voice_start", 1), ("voice_end", 2)]
        a, b = nuxiva_native.RustDuplex("", 0), duplex.PyDuplex("", 0)
        for code, at in script:
            self.assertEqual(a.trigger(code, at), b.trigger(code, at))
        self.assertEqual(a.begin_reply(3), b.begin_reply(3))
        fa, fb = a.bind(1), b.bind(1)
        self.assertEqual(json.loads(a.cut(0, 50)), json.loads(b.cut(0, 50)))
        self.assertEqual((fa.is_cancelled(), fb.is_cancelled()), (True, True))
        self.assertEqual(json.loads(a.snapshot()), json.loads(b.snapshot()))
        self.assertEqual(json.loads(a.events()), json.loads(b.events()))


if __name__ == "__main__":
    unittest.main()
