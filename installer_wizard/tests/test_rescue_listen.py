import random
import sys
import unittest
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
for p in (str(ROOT), str(ROOT / "backend"), str(ROOT / "features" / "ear")):
    if p not in sys.path:
        sys.path.insert(0, p)

import native_core
from features.ear import distress
from features.ear.danger import DangerEar
from features.ear.distress_rules import PHRASES
from features.rescue.detector import detect_speech_intent

RATE = 16000
NATIVE = native_core.symbol("ear_distress") is not None
SOUND = native_core.symbol("RustDangerSound") is not None
TEXTS = [
    "Aiuto!", "aiuto aiuto", "help me", "Au secours !", "¡Socorro!", "chiamate il 118 presto", "Non riesco ad alzarmi",
    "I can't breathe", "je n'arrive pas à me lever", "no puedo respirar", "non ho bisogno di aiuto", "I don't need help",
    "non chiamate l'ambulanza", "aiutami a scrivere una mail", "help me with the recipe", "nel film gridava aiuto",
    "come si dice aiuto in inglese", "sì sto bene", "no, sto bene", "non sto bene", "I'm fine", "no", "sì", "ok",
    "falso allarme", "lasciami, mi fai male!", "al fuoco! c'è fumo", "Nuxiva accendi la luce", "", "   ",
    "ha detto aiuto ridendo", "mi sento male, chiama un'ambulanza", "tout va bien", "estoy bien gracias",
    "Ich brauche Hilfe", "AIUTO MI FA MALE IL PETTO", "non so cosa fare aiuto", "help! help! help!",
]


def close(test, a, b, path=""):
    if isinstance(a, float) or isinstance(b, float):
        test.assertAlmostEqual(float(a), float(b), places=9, msg=path)
    elif isinstance(a, dict):
        test.assertEqual(set(a), set(b), path)
        for k in a:
            close(test, a[k], b[k], f"{path}.{k}")
    elif isinstance(a, list):
        test.assertEqual(len(a), len(b), path)
        for i, (x, y) in enumerate(zip(a, b)):
            close(test, x, y, f"{path}[{i}]")
    else:
        test.assertEqual(a, b, path)


class DistressFallbackTest(unittest.TestCase):
    def test_help_in_four_languages(self):
        for text in ("Aiuto!", "help me", "Au secours", "¡Socorro!", "Non riesco ad alzarmi", "I can't breathe"):
            verdict = distress.py_analyze(text, False, False, 0.9)
            self.assertGreater(verdict["help"], 0.7, text)
            self.assertEqual(verdict["answer"], "not_ok", text)

    def test_negations_tasks_and_films(self):
        self.assertLess(distress.py_analyze("non ho bisogno di aiuto")["help"], 0.05)
        self.assertLess(distress.py_analyze("aiutami a scrivere una mail")["help"], 0.3)
        self.assertLess(distress.py_analyze("nel film gridava aiuto")["help"], 0.4)
        self.assertGreater(distress.py_analyze("non so cosa fare aiuto")["help"], 0.5)

    def test_speech_intent_respects_negation(self):
        self.assertEqual(detect_speech_intent("aiuto", prefer_native=False)[0], "help_words")
        self.assertIsNone(detect_speech_intent("non ho bisogno di aiuto", prefer_native=False)[0])
        self.assertEqual(detect_speech_intent("tutto a posto", prefer_native=False)[0], "all_clear")

    def test_answers(self):
        self.assertEqual(distress.py_analyze("no, sto bene", True)["answer"], "ok")
        self.assertEqual(distress.py_analyze("no", True)["answer"], "not_ok")
        self.assertIsNone(distress.py_analyze("no", False)["answer"])

    def test_danger_ear_words(self):
        ear = DangerEar()
        self.assertIsNone(ear.text("accendi la luce", False))
        self.assertIsNone(ear.text("no", False))
        ear.ask(30)
        verdict = ear.text("no", False)
        self.assertEqual(verdict["answer"], "not_ok")
        self.assertTrue(verdict["asked"])
        self.assertFalse(ear.asked())
        ear.ask("x")
        self.assertTrue(ear.asked())


@unittest.skipUnless(NATIVE, "modulo nativo assente")
class DistressParityTest(unittest.TestCase):
    def test_curated(self):
        for text in TEXTS:
            for asked in (False, True):
                for media in (False, True):
                    close(self, distress.analyze(text, asked, media, 0.85),
                          distress.py_analyze(text, asked, media, 0.85), f"{text!r}:{asked}:{media}")

    def test_random_sentences(self):
        rnd = random.Random(11)
        vocab = [p[0] for p in PHRASES] + ["non", "il", "film", "con", "a", "ha detto", "Nuxiva", "ciao", "luce", "!", "?",
                                           "bisogno", "di", "need", "don't", "très", "perché", "ok", "sì", "no"]
        for _ in range(500):
            text = " ".join(rnd.choice(vocab) for _ in range(rnd.randint(0, 9)))
            asked = rnd.random() < 0.5
            close(self, distress.analyze(text, asked, False, 0.7), distress.py_analyze(text, asked, False, 0.7), text)

    def test_speech_intent_parity(self):
        for text in TEXTS:
            native = detect_speech_intent(text)
            python = detect_speech_intent(text, prefer_native=False)
            self.assertEqual(native[0], python[0], text)
            self.assertAlmostEqual(native[1], python[1], places=9, msg=text)

    def test_every_phrase_matches_alone(self):
        for phrase, cue, _, _ in PHRASES:
            verdict = distress.analyze(phrase)
            self.assertIn(cue, [d["cue"] for d in verdict["detections"]], phrase)


def tone(seconds, f0, harmonics, amp, vibrato):
    t = np.arange(int(seconds * RATE)) / RATE
    f = f0 * (1 + vibrato * np.sin(2 * np.pi * 6 * t))
    phase = np.cumsum(2 * np.pi * f / RATE)
    wave = np.sin(phase) + sum(a * np.sin(phase * (i + 2)) for i, a in enumerate(harmonics))
    return (wave * amp).astype(np.float32)


def quiet(seconds, rng):
    return (rng.uniform(-1, 1, int(seconds * RATE)) * 0.002).astype(np.float32)


@unittest.skipUnless(SOUND, "modulo nativo assente")
class DangerSoundTest(unittest.TestCase):
    def feed(self, signal, media=False, speaking=False):
        ear = DangerEar()
        found = []
        for i in range(0, len(signal), 480):
            found += ear.frame(signal[i:i + 480], media, speaking)
        return found

    def test_scream_and_silence_while_speaking(self):
        rng = np.random.default_rng(1)
        signal = np.concatenate([quiet(1.5, rng), tone(0.9, 1100, [0.6, 0.4], 0.3, 0.03), quiet(1.0, rng)])
        self.assertIn("scream", [e["kind"] for e in self.feed(signal)])
        self.assertEqual(self.feed(signal, speaking=True), [])

    def test_smoke_alarm(self):
        rng = np.random.default_rng(2)
        parts = [quiet(1.5, rng)]
        for _ in range(2):
            for _ in range(3):
                parts += [tone(0.5, 3200, [], 0.2, 0.0), quiet(0.5, rng)]
            parts.append(quiet(1.2, rng))
        kinds = [e["kind"] for e in self.feed(np.concatenate(parts))]
        self.assertEqual(kinds.count("smoke_alarm"), 2)


if __name__ == "__main__":
    unittest.main()
