import random
import unittest

import native_core

from agenti.brain.privacy import detector

FRAGMENTS = [
    "IT60 X054 2811 1010 0000 0123 456", "it60x0542811101000000123456", "RSSMRA85T10A562S", "rssmra85t10a562s",
    "password", "PIN", "otp", "codice segreto", "codice di sicurezza", "analisi del sangue", "blood test", "Diagnosi",
    "mario.rossi@example.com", "a@b.co", "x@y", "me+tag@sub.dom.example.org", "+39 333 1234567", "333 1234567",
    "0612345678", "+1-202-555-0143", "3331234567", "33312345678901", "4111 1111 1111 1111", "4111-1111-1111-1111",
    "4111111111111111", "4111 1111 1111 1112", "5500 0000 0000 0004", "378282246310005", "1234567890123456789012",
    "mia moglie", "my salary", "abito a Roma", "stipendio", "conto corrente", "giulia", "marco rossi", "luca",
    "ciao", "che tempo fa", "accendi la luce", "è tutto ok", "à è ì ò ù", "çà", "straße", "Äpfel", " ", "\n", "\t",
    "12 34 56", "1-2-3-4-5-6-7-8-9-0-1-2-3", "9 9 9 9 9 9 9 9 9 9 9 9 9 9 9 9 9 9 9 9",
]
FILLERS = [" ", ", ", ". ", "-", "+", "(", ")", "\n", "x", "9", "0", "3", "é", "ñ", "ª", "²", "µ", "ı", "İ", "ſ", "K"]
NAMES = [("giulia", "marco rossi", "luca"), (), ("ana",), ("jo",), ("müller", "señor")]


def build(rng):
    parts = []
    for _ in range(rng.randint(1, 6)):
        parts.append(rng.choice(FRAGMENTS) if rng.random() < 0.7 else rng.choice(FILLERS))
        parts.append(rng.choice(FILLERS) if rng.random() < 0.5 else "")
    text = "".join(parts)
    if rng.random() < 0.2:
        pos = rng.randrange(len(text) + 1)
        text = text[:pos] + rng.choice(FILLERS) + text[pos:]
    return text


@unittest.skipIf(native_core.symbol("RustPrivacy") is None, "modulo nativo assente")
class PrivacyParityTest(unittest.TestCase):
    def test_fixed_cases(self):
        for text in FRAGMENTS:
            for names in NAMES:
                with self.subTest(text=text, names=names):
                    self.assertEqual(detector.classify_all([text], names), detector._py_classify_all([text], names))

    def test_differential_fuzz(self):
        rng = random.Random(20261114)
        for _ in range(4000):
            texts = [build(rng) for _ in range(rng.randint(1, 3))]
            names = rng.choice(NAMES)
            with self.subTest(texts=texts, names=names):
                self.assertEqual(detector.classify_all(texts, names), detector._py_classify_all(texts, names))

    def test_native_never_weaker_than_python(self):
        engine = native_core.symbol("RustPrivacy")()
        rank = {"public": 0, "personal": 1, "sensitive": 2}
        rng = random.Random(7)
        for _ in range(3000):
            text = build(rng)
            kind, level = engine.classify_all([text], [])
            if kind == "level":
                self.assertGreaterEqual(rank[level], rank[detector._py_classify_all([text], [])], text)

    def test_exotic_defers(self):
        engine = native_core.symbol("RustPrivacy")()
        self.assertEqual(engine.classify_all(["日本語"], [])[0], "defer")
        self.assertEqual(engine.classify_all(["pın"], [])[0], "defer")
        self.assertEqual(engine.classify_all(["ciao"], []), ("level", "public"))

    def test_oversized_text_is_bounded(self):
        text = "1 " * 30000
        self.assertEqual(detector.classify_all([text], ()), detector._py_classify_all([text], ()))


class PrivacyFallbackTest(unittest.TestCase):
    def test_python_engine_stands_alone(self):
        self.assertEqual(detector._py_classify_all(["la mia password"], ()), "sensitive")


if __name__ == "__main__":
    unittest.main()
