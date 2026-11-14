import json
import unittest
from pathlib import Path

from agenti.ear import duplex, merge

try:
    import nuxiva_native
except ImportError:
    nuxiva_native = None

NATIVE = nuxiva_native is not None and hasattr(nuxiva_native, "RustMerge")
RUST_CATALOG = Path(__file__).resolve().parents[2] / "native" / "crates" / "duplex-core" / "src" / "intents.json"
CASES = [
    ("no aspetta", "cancel"), ("Stop!", "cancel"), ("basta così", "cancel"), ("lascia stare", "cancel"),
    ("continua", "continue"), ("Vai avanti pure", "continue"), ("scusa continua", "continue"),
    ("fammi un'altra versione", "modify"), ("fammi un’altra versione", "modify"), ("più breve per favore", "modify"),
    ("no aspetta fammi un'altra versione", "modify"), ("ripeti", "modify"),
    ("no aspetta dimmi che tempo fa domani a Milano", "replace"),
    ("continua a leggermi le notizie sportive di oggi", "unrelated"), ("che ore sono", "unrelated"), ("", "unrelated"), ("...", "unrelated"),
]


class Common:
    def make(self):
        raise NotImplementedError

    def session(self):
        raise NotImplementedError

    def interrupted_session(self):
        s = self.session()
        s.trigger("voice_start", 1)
        s.trigger("voice_end", 2)
        epoch = s.begin_reply(3)
        s.mark_spoken(epoch, 20)
        s.cut(epoch, 500)
        return s

    def test_corpus(self):
        m = self.make()
        for text, intent in CASES:
            self.assertEqual(json.loads(m.classify(text)), intent, text)

    def test_plan_follows_intent_and_reference(self):
        m, s = self.make(), self.interrupted_session()
        reply = m.interrupted(s, "Ecco la ricetta: prendi", "fasc:r1")
        self.assertEqual(json.loads(reply), {"spoken_text": "Ecco la ricetta: prendi", "unspoken_ref": "fasc:r1", "interrupted_at_ms": 500, "spoken_chars": 20})
        self.assertEqual(json.loads(m.plan(reply, "continua"))["resume_ref"], "fasc:r1")
        self.assertEqual(json.loads(m.plan(reply, "più breve"))["regenerate_ref"], "fasc:r1")
        cancel = json.loads(m.plan(reply, "no aspetta"))
        self.assertTrue(cancel["drop_previous"])
        self.assertIsNone(cancel["resume_ref"])
        self.assertFalse(json.loads(m.plan(reply, "che ore sono"))["drop_previous"])

    def test_bad_input_is_refused(self):
        m, s = self.make(), self.interrupted_session()
        for ref in ("x y", "../etc", "a" * 129):
            with self.assertRaises(ValueError):
                m.interrupted(s, "t", ref)
        with self.assertRaises(ValueError):
            m.plan("not json", "ok")
        with self.assertRaises(ValueError):
            m.interrupted(self.session(), "t", None)


class PythonFallbackTest(Common, unittest.TestCase):
    def make(self):
        return merge.PyMerge()

    def session(self):
        return duplex.PyDuplex("", 0)


@unittest.skipUnless(NATIVE, "modulo nativo non installato")
class NativeTest(Common, unittest.TestCase):
    def make(self):
        return nuxiva_native.RustMerge()

    def session(self):
        return nuxiva_native.RustDuplex("", 0)

    def test_catalogs_are_identical_and_results_agree(self):
        self.assertEqual(json.loads(RUST_CATALOG.read_text(encoding="utf-8")), json.loads(merge.CATALOG.read_text(encoding="utf-8")))
        a, b = nuxiva_native.RustMerge(), merge.PyMerge()
        for text, _ in CASES + [("Aspetta un attimo, ", "x"), ("Più semplice!", "x")]:
            self.assertEqual(a.classify(text), b.classify(text), text)

    def test_bad_catalog_is_refused(self):
        for bad in ("{}", '{"cancel":[],"continue":["a"],"modify":["b"]}'):
            with self.assertRaises(ValueError):
                nuxiva_native.RustMerge(bad)


if __name__ == "__main__":
    unittest.main()
