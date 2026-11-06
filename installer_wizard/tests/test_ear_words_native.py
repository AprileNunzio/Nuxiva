import importlib.util
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import numpy as np

EAR = Path(__file__).resolve().parents[1] / "features" / "ear"
if str(EAR) not in sys.path:
    sys.path.append(str(EAR))

import native_core
import words


def _load_stt():
    spec = importlib.util.spec_from_file_location("nuxiva_ear_stt_words", EAR / "stt.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


stt = _load_stt()

NATIVE = native_core.symbol("RustLexicon") is not None
TERMS = ["Nuxiva", "Nunzio", "Giulia", "Soggiorno", "Lampada Arco", "Ciabatta TV"]


def word(text, prob):
    return SimpleNamespace(word=text, probability=prob)


def segment(text, parts=(), logprob=-0.2, no_speech=0.05, ratio=1.2):
    return SimpleNamespace(text=text, avg_logprob=logprob, no_speech_prob=no_speech, compression_ratio=ratio,
                           words=[word(t, p) for t, p in parts])


class Clock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now


@unittest.skipUnless(NATIVE, "modulo nativo assente")
class WordFixerTest(unittest.TestCase):

    def setUp(self):
        self.clock = Clock()
        self.fixer = words.WordFixer(lambda: TERMS, clock=self.clock)

    def test_uncertain_names_are_fixed_with_the_home_vocabulary(self):
        heard = self.fixer.hear([segment(" Dove è Nunsio?", [(" Dove", 0.9), (" è", 0.9), (" Nunsio", 0.3), ("?", 0.9)])],
                                "Ehi, Nuxiva.", stt.HALLUCINATIONS)
        self.assertEqual(heard.text, "Dove è Nunzio?")
        self.assertEqual([f[1] for f in heard.fixes], ["Nunzio"])
        heard = self.fixer.hear([segment(" accendi la lampada arcò", [(" accendi", 0.95), (" la", 0.95), (" lampada", 0.6),
                                                                      (" arcò", 0.3)])], "", stt.HALLUCINATIONS)
        self.assertEqual(heard.text, "accendi la Lampada Arco")

    def test_confident_words_stay_as_heard(self):
        heard = self.fixer.hear([segment(" che tempo fa a marzo", [(" che", 0.95), (" tempo", 0.95), (" fa", 0.9), (" a", 0.9),
                                                                   (" marzo", 0.93)])], "", stt.HALLUCINATIONS)
        self.assertEqual(heard.text, "che tempo fa a marzo")
        self.assertEqual(heard.fixes, ())

    def test_noise_phrases_silence_and_loops_are_dropped(self):
        heard = self.fixer.hear([segment(" accendi la luce", [(" accendi", 0.9), (" la", 0.9), (" luce", 0.9)]),
                                 segment(" Sottotitoli a cura di QTSS"),
                                 segment(" boh", logprob=-1.5, no_speech=0.9),
                                 segment(" sì sì sì sì sì sì"),
                                 segment(" assistente digitale", logprob=-0.8)],
                                "Ehi, Nuxiva, assistente digitale.", stt.HALLUCINATIONS)
        self.assertEqual(heard.text, "accendi la luce")
        self.assertEqual([why for _, why in heard.dropped],
                         ["frase tipica di rumore", "silenzio", "ripetizione", "copia del suggerimento"])

    def test_recent_words_help_and_the_prompt_carries_the_last_sentence(self):
        self.assertEqual(self.fixer.prompt_tail(), "")
        self.fixer.remember("accendi la luce in soggiorno")
        self.assertIn("soggiorno", self.fixer.context())
        self.assertEqual(self.fixer.prompt_tail(), "accendi la luce in soggiorno")
        self.clock.now += 90
        self.assertEqual(self.fixer.prompt_tail(), "")
        self.assertIn("soggiorno", self.fixer.context())
        self.clock.now += 60
        self.assertEqual(self.fixer.context(), [])

    def test_lexicon_follows_vocabulary_changes(self):
        terms = ["Nunzio"]
        fixer = words.WordFixer(lambda: terms, clock=self.clock)
        first = fixer._lexicon()
        terms.append("Giulia")
        self.assertIs(fixer._lexicon(), first)
        self.clock.now += 61
        self.assertIsNot(fixer._lexicon(), first)
        self.assertEqual(len(fixer._lexicon()), 2)

    def test_invalid_input_is_rejected(self):
        engine = native_core.symbol("RustLexicon")
        with self.assertRaises(ValueError):
            engine(["x"] * 5000)
        with self.assertRaises(ValueError):
            engine(TERMS).correct([("x", 0.5)] * 600)
        text, fixes = engine(TERMS).correct([(" Nunsio", float("nan"))])
        self.assertEqual((text, len(fixes)), (" Nunzio", 1))

    def test_stt_uses_beam_words_and_correction(self):
        model = mock.Mock()
        model.transcribe.return_value = ([segment(" ciao Giuglia", [(" ciao", 0.9), (" Giuglia", 0.4)])], None)
        with mock.patch.dict(stt.ACTIVE, {"model": model}), mock.patch.object(stt, "FIXER", self.fixer), \
                mock.patch.dict("os.environ", {"NUXIVA_EAR_MODE": "offline"}):
            text, _ = stt.transcribe(np.zeros(16000, dtype=np.float32), fast=False, detect=False)
        self.assertEqual(text, "ciao Giulia")
        kwargs = model.transcribe.call_args.kwargs
        self.assertEqual(kwargs["beam_size"], stt.BEAM)
        self.assertEqual(kwargs["word_timestamps"], stt.WORD_CHECK)
        self.assertEqual(self.fixer.prompt_tail(), "ciao Giulia")


class WordFallbackTest(unittest.TestCase):

    def test_python_fallback_keeps_previous_behaviour(self):
        with mock.patch.object(native_core, "symbol", return_value=None):
            fixer = words.WordFixer(lambda: TERMS)
        self.assertFalse(fixer.native)
        self.assertEqual(fixer.hear([segment(" ciao Giuglia")], "", stt.HALLUCINATIONS).text, "ciao Giuglia")
        self.assertEqual(fixer.hear([segment(" Grazie.")], "", stt.HALLUCINATIONS).text, "")

    def test_mock_segments_without_scores_are_accepted(self):
        fixer = words.WordFixer(lambda: TERMS)
        heard = fixer.hear([mock.Mock(text="ciao Nuxiva")], "", stt.HALLUCINATIONS)
        self.assertEqual(heard.text, "ciao Nuxiva")


if __name__ == "__main__":
    unittest.main()
