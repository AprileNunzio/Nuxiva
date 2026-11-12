import itertools
import unittest
from unittest import mock

import native_core

from features.chat import addressee

TEXTS = [
    "nuxiva accendi la luce", "Ehi Nuxiva che ore sono?", "nuxiva è lenta oggi", "attena spegni tutto",
    "accendi la luce in cucina", "che tempo fa domani?", "mah", "ok", "sì grazie", "no lascia stare",
    "Marco passami il sale", "secondo te va bene così", "lui non capisce niente", "il computer è rotto",
    "e domani a Roma?", "domani piove a Roma", "puoi ripetere", "ho visto un film bellissimo ieri sera",
    "dimmi una barzelletta", "questo coso non funziona", "perché il cielo è blu", "",
    "Giulia, che ne pensi?", "ÈCCO, accendi la TV", "àèìòù perché?", "NUXIVA, sei lì?", "Nuxivà spegni",
]

SCENES = [
    addressee.Scene(alone=True, facing=False, asked_question=False, since_reply=1e9, last_turn=None,
                    present_names=(), alone_score=0.35, threshold=0.5),
    addressee.Scene(alone=False, facing=False, asked_question=False, since_reply=5.0, last_turn="che tempo fa a Roma domani pioggia",
                    present_names=("marco", "giulia"), alone_score=0.35, threshold=0.5),
    addressee.Scene(alone=False, facing=True, asked_question=True, since_reply=30.0, last_turn="vuoi che accenda la luce?",
                    present_names=("marco",), alone_score=0.35, threshold=0.6, same_speaker=True, voices_active=2),
    addressee.Scene(alone=True, facing=False, asked_question=False, since_reply=40.0, last_turn="film",
                    present_names=(), alone_score=0.2, threshold=0.4, same_speaker=False, voices_active=3,
                    mixed_speakers=True),
    addressee.Scene(alone=False, facing=False, asked_question=False, since_reply=90.0, last_turn=None,
                    present_names=("giulia",), alone_score=0.35, threshold=0.5, same_speaker=True, voices_active=1,
                    mixed_speakers=False),
]


def env(name="Nuxiva", aliases=""):
    values = {"NUXIVA_ASSISTANT_NAME": name, "NUXIVA_WAKE_PHONETIC_ALIASES": aliases}
    return mock.patch.object(addressee, "env_get", side_effect=lambda k, d="": values.get(k, d))


@unittest.skipIf(native_core.symbol("RustAddressee") is None, "modulo nativo assente")
class AddresseeParityTest(unittest.TestCase):

    def test_rust_matches_python_on_every_text_and_scene(self):
        with env():
            for text, ctx in itertools.product(TEXTS, SCENES):
                with self.subTest(text=text, ctx=ctx):
                    self.assertEqual(addressee.decide(text, ctx), addressee._py_decide(text, ctx))

    def test_custom_name_and_aliases(self):
        ctx = SCENES[1]
        with env("Hey Jarvis", "giarvis, gervis"):
            for text in ("jarvis accendi", "giarvis che ore sono", "gervis è lento", "nuxiva accendi", "attena spegni"):
                with self.subTest(text=text):
                    self.assertEqual(addressee.decide(text, ctx), addressee._py_decide(text, ctx))
            self.assertTrue(addressee.decide("giarvis che ore sono", ctx).directed)
            self.assertFalse(addressee.decide("attena spegni", ctx).reason == "mi ha chiamato per nome")

    def test_voice_turns_move_the_decision(self):
        base = SCENES[1]
        with env():
            plain = addressee.decide("ho visto un film", base)
            same = addressee.decide("ho visto un film", addressee.Scene(**{**base.__dict__, "same_speaker": True}))
            crowd = addressee.decide("ho visto un film", addressee.Scene(**{**base.__dict__, "voices_active": 3}))
            mixed = addressee.decide("ho visto un film", addressee.Scene(**{**base.__dict__, "mixed_speakers": True}))
        self.assertGreater(same.score, plain.score)
        self.assertIn("stessa persona di prima", same.reason)
        self.assertLess(crowd.score, plain.score)
        self.assertLess(mixed.score, plain.score)

    def test_invalid_context_is_rejected(self):
        rules = native_core.symbol("RustAddressee")("Nuxiva")
        with self.assertRaises(ValueError):
            rules.judge("ciao", alone=True, facing=False, asked_question=False, since_reply=1.0,
                        present_names=["x" * 500])
        with self.assertRaises(ValueError):
            native_core.symbol("RustAddressee")("n" * 500)
        directed, score, reason = rules.judge("x" * 20000, alone=True, facing=False, asked_question=False,
                                              since_reply=float("nan"))
        self.assertFalse(directed)
        self.assertEqual(reason, "testo troppo lungo")


class AddresseeContextTest(unittest.TestCase):

    def test_heard_fields_are_sanitised(self):
        self.assertIsNone(addressee.flag("true"))
        self.assertTrue(addressee.flag(True))
        self.assertIsNone(addressee.voices(True))
        self.assertEqual(addressee.voices(500), 64)
        self.assertEqual(addressee.voices(-3), 0)
        self.assertIsNone(addressee.voices("2"))

    def test_python_fallback_when_native_missing(self):
        with env(), mock.patch.object(native_core, "symbol", return_value=None):
            verdict = addressee.decide("accendi la luce", SCENES[0])
        self.assertTrue(verdict.directed)
        self.assertEqual(verdict.reason, "comando")


if __name__ == "__main__":
    unittest.main()
