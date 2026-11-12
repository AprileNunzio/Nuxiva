import json
import random
import re
import unittest

from agenti.team import routing
from agenti.team.relevance import GENERIC
from agenti.team.scanner import scanner
from agenti.team.stopwords import ALL_STOPWORDS, clean_tokens, is_conversational_query

try:
    import nuxiva_native
except ImportError:
    nuxiva_native = None

NATIVE = nuxiva_native is not None and hasattr(nuxiva_native, "RustCeoIndex")
TEXTS = [
    "", "   ", "ciao", "Ciao Nuxiva, come va?", "BUONGIORNO!!", "hı", "chi sei?", "cosa sai fare", "how are you today",
    "¿cómo estás?", "comment ça va", "wie geht's", "tudo bem", "ciao\x1ccome stai", "Mi mostri una medusa",
    "l’home_assistant accende il SALOTTO-2", "quanti battiti ho e quanto stress", "ſalotto ıncredibile",
    "metti un po' di musica rock", "apri la lavagna e disegna un triangolo", "com'è finito il Napoli ieri sera",
    "creami un sito per la pizzeria di Mario", "accendi la luce del salotto", "fammi vedere la telecamera del giardino",
    "che tempo fa domani a Roma", "x" * 9000, "medusa " * 3000, "İstanbul Kelvin K tempo", "the vision agent please",
]


def _corpus(agents) -> list[str]:
    words: list[str] = []
    for agent in agents.values():
        words.extend(str(n) for n in agent.routing.get("nouns", []))
        words.extend(agent.name.split())
        words.append(agent.id)
    rnd = random.Random(20261112)
    extra = [" ".join(rnd.sample(words, k=rnd.randint(1, 5))) for _ in range(300)]
    return TEXTS + extra


@unittest.skipUnless(NATIVE, "nuxiva_native non disponibile")
class CeoNativeParityTest(unittest.TestCase):
    def test_lexicon_matches_python(self):
        stop, generic = nuxiva_native.ceo_lexicon()
        wanted = {w for w in ALL_STOPWORDS if re.fullmatch(r"[a-z0-9_-]{3,}", w)}
        self.assertEqual(set(stop), wanted)
        self.assertEqual(set(generic), set(GENERIC))

    def test_tokens_and_conversation_match_python(self):
        for text in TEXTS:
            with self.subTest(text=text[:40]):
                self.assertEqual(sorted(nuxiva_native.ceo_clean_tokens(text)), sorted(clean_tokens(text[:4096])))
                self.assertEqual(nuxiva_native.ceo_is_conversational(text), is_conversational_query(text[:4096]))

    def test_decisions_match_python(self):
        agents = scanner.scan()
        native = routing.Router(native=True)
        python = routing.Router(native=False)
        self.assertEqual(native.engine, "rust")
        learned = {"medus": {"particles": 3}, "nuvol": {"weather": 9}}
        for text in _corpus(agents):
            with self.subTest(text=text[:40]):
                a = native.decide(agents, text, learned, 1)
                b = python.decide(agents, text, learned)
                self.assertEqual(a, b)

    def test_real_manifest_phrases_compile(self):
        agents = scanner.scan()
        payload = json.dumps([routing.card(a) for a in agents.values()])
        index = nuxiva_native.RustCeoIndex(payload)
        self.assertEqual(index.invalid_phrases(), [])
        self.assertEqual(len(index), len(agents))

    def test_hostile_payloads_are_refused(self):
        with self.assertRaises(ValueError):
            nuxiva_native.RustCeoIndex("{")
        with self.assertRaises(ValueError):
            nuxiva_native.RustCeoIndex("[" + " " * (17 * 1024 * 1024) + "]")
        index = nuxiva_native.RustCeoIndex(json.dumps([{"id": "a", "phrases": ["(?<=x)y", "(" * 600]}]))
        self.assertEqual(len(index.invalid_phrases()), 2)
        with self.assertRaises(ValueError):
            index.set_learned('{"a": {"b": -1}}')
        json.loads(index.decide("a" * 100_000))


if __name__ == "__main__":
    unittest.main()
