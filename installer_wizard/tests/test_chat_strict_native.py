import unittest

import native_core

from agenti.chat import strict_reply

CORPUS = [
    "quanto fa 12 per 12? rispondi solo con il numero", "What is 7 times 6? reply with only the number.",
    "quanto fa -3 + 10? rispondi solo con il numero", "quanto fa 5 − 9? rispondi solo con il numero",
    "quanto fa 5 - 9? rispondi solo con il numero", "QUANTO FA 2 PER 3? RISPONDI SOLO CON IL NUMERO",
    "quanto fa 999999999999 per 999999999999? rispondi solo con il numero",
    "quanto fa 3 × 4? rispondi solo con il numero", "quanto fa 3 * 4 ? rispondi solo con il numero",
    "quanto fa ٣ per 4? rispondi solo con il numero", "quanto fa 1234567890123 per 2? rispondi solo con il numero",
    "  quanto fa 2 per 2? rispondi solo con il numero  ", "quanto fa 2 per 2 rispondi solo con il numero",
    "ordina in ordine alfabetico: pera, Mela, banana.", "sort alphabetically: zebra, Äpfel, apple",
    "ordina alfabeticamente: solo", "ordina alfabeticamente: a1, b", "ordina alfabeticamente : x, y",
    "ordina alfabeticamente: straße, strasse, Strand", "ordina alfabeticamente: œuf, oeuf, ſoup, soup",
    "ordina alfabeticamente: αβγ, δ", "ordina alfabeticamente: école, ecole", "ordina alfabeticamente: ², a",
    "ordina alfabeticamente: Zoë, zoe, ZOE, Zoé", "ordina alfabeticamente: sant'angelo, san-marco, san marco",
    "ordina alfabeticamente: a,,b", "ordina alfabeticamente: ", "ordina alfabeticamente: a, b, c, d.\n",
    "\u001cordina alfabeticamente: a, b", "ciao come stai", "", "ordina alfabeticamente: İstanbul, istanbul, Izmir",
    "ordina alfabeticamente: ǅ, ǆ, dz", "ordina alfabeticamente: " + ", ".join(f"w{'a' * (i % 7)}" for i in range(50)),
    "ordina alfabeticamente: " + ", ".join("x" * 3 for _ in range(1100)),
]


@unittest.skipIf(native_core.symbol("RustStrictReply") is None, "modulo nativo assente")
class StrictReplyParityTest(unittest.TestCase):
    def test_delegate_matches_python_engine(self):
        for text in CORPUS:
            with self.subTest(text=text[:60]):
                self.assertEqual(strict_reply.deterministic(text), strict_reply._py_deterministic(text))

    def test_defer_is_reserved_for_exotic_input(self):
        engine = native_core.symbol("RustStrictReply")()
        self.assertEqual(engine.deterministic("quanto fa 2 per 3? rispondi solo con il numero"), ("answer", "6"))
        self.assertEqual(engine.deterministic("ciao")[0], "none")
        self.assertEqual(engine.deterministic("ordina alfabeticamente: αβγ, δ")[0], "defer")


class StrictReplyFallbackTest(unittest.TestCase):
    def test_python_engine_stands_alone(self):
        self.assertEqual(strict_reply._py_deterministic("ordina alfabeticamente: b, a"), "a, b")


if __name__ == "__main__":
    unittest.main()
