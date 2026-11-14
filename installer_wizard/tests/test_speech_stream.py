import asyncio
import unittest

from agenti.ear import duplex, speech_stream

try:
    import nuxiva_native
except ImportError:
    nuxiva_native = None

NATIVE = nuxiva_native is not None and hasattr(nuxiva_native, "RustChunker")
CASES = [
    ["Ciao, sono ", "Nuxiva. ", "Come ", "stai", "? ", "Bene"],
    ["Costa 3.5 euro e arriva alle 10.30 con la U.S.A. Express. Fine"],
    ["Il 12. maggio ci vediamo. Ciao"],
    ["Parla il dott. Rossi con A. Bianchi ecc. e poi esce. Fine"],
    ["Si, ", "certo che posso aiutarti con questo, ", "dimmi pure"],
    ["Misura 3,5 metri di lunghezza totale. Fine"],
    ["Perché è già così… davvero? Sì, però ", "più tardi"],
    ["parola " * 120],
    ["x" * 700],
]


def run(chunker, tokens):
    out = []
    for i, t in enumerate(tokens):
        out += chunker.push(t, i)
    return out + chunker.flush(1000)


class FakeStream:
    def __init__(self, tokens):
        self.tokens = tokens

    def __aiter__(self):
        return self._gen()

    async def _gen(self):
        for t in self.tokens:
            yield t


class Flag:
    def __init__(self):
        self.cancelled = False

    def is_cancelled(self):
        return self.cancelled


class Common:
    def make(self):
        raise NotImplementedError

    def test_sentences_and_protected_tokens(self):
        self.assertEqual(run(self.make(), CASES[0]), ["Ciao, sono Nuxiva.", "Come stai?", "Bene"])
        self.assertEqual(run(self.make(), CASES[1]), ["Costa 3.5 euro e arriva alle 10.30 con la U.S.A. Express.", "Fine"])
        self.assertEqual(run(self.make(), CASES[2]), ["Il 12. maggio ci vediamo.", "Ciao"])
        self.assertEqual(run(self.make(), CASES[3]), ["Parla il dott. Rossi con A. Bianchi ecc. e poi esce.", "Fine"])
        self.assertEqual(run(self.make(), CASES[5]), ["Misura 3,5 metri di lunghezza totale.", "Fine"])

    def test_clause_and_timeout(self):
        self.assertEqual(run(self.make(), CASES[4]), ["Si, certo che posso aiutarti con questo,", "dimmi pure"])
        c = self.make()
        c.push("questa frase non finisce mai e continua ancora un po", 0)
        self.assertEqual(c.poll(349), [])
        self.assertEqual(c.poll(350), ["questa frase non finisce mai e continua ancora un"])
        self.assertEqual(c.flush(400), ["po"])

    def test_long_text_is_capped_without_loss(self):
        out = run(self.make(), CASES[7])
        self.assertTrue(all(len(x) <= 240 for x in out))
        self.assertEqual(" ".join(out), CASES[7][0].strip())
        self.assertTrue(all(len(x) <= 240 for x in run(self.make(), CASES[8])))

    def test_stream_stops_when_cancelled(self):
        flag, said = Flag(), []

        async def speak(text):
            said.append(text)
            flag.cancelled = True

        count = asyncio.run(speech_stream.stream_reply(FakeStream(["Prima frase. ", "Seconda frase. ", "Terza. "]), speak, flag, self.make(), lambda: 0))
        self.assertEqual((count, said), (1, ["Prima frase."]))


class PythonFallbackTest(Common, unittest.TestCase):
    def make(self):
        return speech_stream.PyChunker()


@unittest.skipUnless(NATIVE, "modulo nativo non installato")
class NativeTest(Common, unittest.TestCase):
    def make(self):
        return nuxiva_native.RustChunker()

    def test_native_and_fallback_agree_on_the_corpus(self):
        for tokens in CASES:
            self.assertEqual(run(nuxiva_native.RustChunker(), tokens), run(speech_stream.PyChunker(), tokens), tokens)

    def test_bad_settings_are_refused(self):
        with self.assertRaises(ValueError):
            nuxiva_native.RustChunker('{"min_chars":0}')


if __name__ == "__main__":
    unittest.main()
