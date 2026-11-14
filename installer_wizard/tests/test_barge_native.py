import json
import unittest
from pathlib import Path

from agenti.ear import barge, duplex

try:
    import nuxiva_native
except ImportError:
    nuxiva_native = None

NATIVE = nuxiva_native is not None and hasattr(nuxiva_native, "RustBarge")
RUST_CATALOG = Path(__file__).resolve().parents[2] / "native" / "crates" / "duplex-core" / "src" / "backchannel.json"
YES = ["mh", "Sì.", "ok", "certo", "ah sì", "va bene", "Esatto!", "mhm mhm", "capito"]
NO = ["no aspetta", "continua", "fammi un'altra versione", "sì però", "dimmi il meteo", "ok ok ok ok", "", "..."]


class Common:
    def make(self):
        raise NotImplementedError

    def session(self):
        raise NotImplementedError

    def speaking(self):
        s = self.session()
        s.trigger("voice_start", 1)
        s.trigger("voice_end", 2)
        s.begin_reply(3)
        return s

    def feed(self, b, s, verdict, margin, voiced, start, frames):
        return [json.loads(b.step(s, verdict, margin, voiced, 50, start + i * 50))["decision"] for i in range(frames)]

    def test_owner_voice_ducks_then_cuts(self):
        b, s = self.make(), self.speaking()
        out = self.feed(b, s, "known", 900, True, 100, 6)
        self.assertEqual(out[:5], ["hold", "duck", "hold", "hold", "cut"])
        self.assertEqual(json.loads(s.snapshot())["state"], "interrupted")
        self.assertEqual(json.loads(b.stats())["cuts"], 1)

    def test_radio_and_unknown_never_cut(self):
        b, s = self.make(), self.speaking()
        for verdict in ("broadcast", "uncertain"):
            self.assertEqual(set(self.feed(b, s, verdict, 1000, True, 100, 400)), {"hold"})
        self.assertEqual(json.loads(s.snapshot())["state"], "speaking")
        self.assertEqual(json.loads(b.stats())["cuts"], 0)

    def test_weak_margin_never_cuts_and_unknown_verdict_is_refused(self):
        b, s = self.make(), self.speaking()
        self.assertEqual(set(self.feed(b, s, "known", 599, True, 100, 50)), {"hold"})
        with self.assertRaisesRegex(ValueError, "duplex.invalid"):
            b.step(s, "mine", 900, True, 50, 0)

    def test_idle_session_is_never_cut(self):
        b, s = self.make(), self.session()
        self.assertEqual(set(self.feed(b, s, "known", 1000, True, 0, 30)), {"hold"})

    def test_duck_is_restored(self):
        b, s = self.make(), self.speaking()
        self.feed(b, s, "known", 900, True, 100, 2)
        self.assertEqual(json.loads(b.tick(3149))["decision"], "hold")
        self.assertEqual(json.loads(b.tick(3150))["decision"], "restore")

    def test_backchannel_catalog(self):
        b = self.make()
        for text in YES:
            self.assertTrue(b.is_backchannel(text), text)
        for text in NO:
            self.assertFalse(b.is_backchannel(text), text)

    def test_risky_commands_need_the_owner(self):
        self.assertTrue(barge.may_command("known", "high"))
        self.assertTrue(barge.may_command("guest", "low"))
        self.assertFalse(barge.may_command("guest", "high"))
        self.assertFalse(barge.may_command("broadcast", "low"))


class PythonFallbackTest(Common, unittest.TestCase):
    def make(self):
        return barge.PyBarge()

    def session(self):
        return duplex.PyDuplex("", 0)

    def test_pre_roll_keeps_the_latest_audio(self):
        ring = barge.PyPreRoll(16000, 600, 2)
        ring.push(b"\x01" * 30000)
        ring.push(b"\x09" * 100)
        snap = ring.snapshot()
        self.assertEqual((len(snap), snap[-100:]), (19200, b"\x09" * 100))


@unittest.skipUnless(NATIVE, "modulo nativo non installato")
class NativeTest(Common, unittest.TestCase):
    def make(self):
        return nuxiva_native.RustBarge()

    def session(self):
        return nuxiva_native.RustDuplex("", 0)

    def test_pre_roll_keeps_the_latest_audio(self):
        ring = nuxiva_native.RustPreRoll(16000, 600, 2)
        ring.push(b"\x01" * 30000)
        ring.push(b"\x09" * 100)
        snap = ring.snapshot()
        self.assertEqual((len(snap), snap[-100:]), (19200, b"\x09" * 100))
        with self.assertRaises(ValueError):
            nuxiva_native.RustPreRoll(100, 600, 2)

    def test_catalogs_are_identical_and_decisions_agree(self):
        self.assertEqual(json.loads(RUST_CATALOG.read_text(encoding="utf-8")), json.loads(barge.CATALOG.read_text(encoding="utf-8")))
        a, b = nuxiva_native.RustBarge(), barge.PyBarge()
        sa, sb = self.speaking(), duplex.PyDuplex("", 0)
        sb.trigger("voice_start", 1)
        sb.trigger("voice_end", 2)
        sb.begin_reply(3)
        script = [("known", 900, True), ("known", 900, True), ("broadcast", 900, True), ("known", 900, True), ("known", 400, True), ("guest", 900, True)] * 6
        for i, (verdict, margin, voiced) in enumerate(script):
            ra, rb = json.loads(a.step(sa, verdict, margin, voiced, 50, 100 + i * 50)), json.loads(b.step(sb, verdict, margin, voiced, 50, 100 + i * 50))
            self.assertEqual(ra["decision"], rb["decision"], i)
        self.assertEqual(json.loads(a.stats()), json.loads(b.stats()))


if __name__ == "__main__":
    unittest.main()
