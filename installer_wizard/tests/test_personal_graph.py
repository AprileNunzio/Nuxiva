import json
import unittest

import native_core

from personal_graph import GraphError, PersonalGraph
from personal_graph.fallback import PyGraph
from personal_graph.primitives import cosine_permille, embed, halve, noisy_or, normalize

PRIMITIVE_CORPUS = [
    "Pasta alla Carbonara",
    "caffè   ESPRESSO!",
    "àèìòù ç ñ ý ÿ ø å",
    "",
    "   ",
    "x" * 300,
    "Ünïcödé Straße",
    "123 456-789",
    "ŞİŁ test",
    "mi piace il caffè",
    "mi piace il caffe",
    "abito a Torino",
]

SCENARIO = [
    {"op": "register", "id": "nunzio", "name": "Nunzio", "role": "family"},
    {"op": "register", "id": "anna", "name": "Anna", "role": "family"},
    {"op": "register", "id": "ospite", "name": "Ospite", "role": "guest"},
    {"op": "remember", "as": "nunzio", "kind": "preference", "label": "pasta alla carbonara", "level": "private"},
    {"op": "remember", "as": "nunzio", "kind": "place", "label": "Roma", "detail": "capitale", "level": "family"},
    {"op": "remember", "as": "anna", "kind": "preference", "label": "vino rosso", "level": "family"},
    {"op": "remember", "as": "anna", "kind": "preference", "label": "vino segreto", "level": "private"},
    {"op": "remember", "as": "ospite", "kind": "preference", "label": "tisana", "level": "public"},
    {"op": "relate", "as": "nunzio", "from": {"kind": "person", "label": "@self"}, "relation": "spouse", "to": {"kind": "person", "label": "Giulia"}, "confidence": 900},
    {"op": "relate", "as": "nunzio", "from": {"kind": "person", "label": "Giulia"}, "relation": "likes", "to": {"kind": "preference", "label": "cioccolato"}, "confidence": 850},
    {"op": "relate", "as": "nunzio", "from": {"kind": "person", "label": "@self"}, "relation": "lives_in", "to": {"kind": "place", "label": "Roma"}, "confidence": 500},
    {"op": "relate", "as": "nunzio", "from": {"kind": "person", "label": "@self"}, "relation": "lives_in", "to": {"kind": "place", "label": "Torino"}, "confidence": 800},
    {"op": "relate", "as": "nunzio", "from": {"kind": "person", "label": "@self"}, "relation": "lives_in", "to": {"kind": "place", "label": "Roma"}, "confidence": 300},
    {"op": "relate", "as": "nunzio", "from": {"kind": "person", "label": "@self"}, "relation": "likes", "to": {"kind": "preference", "label": "caffè"}, "confidence": 700},
    {"op": "relate", "as": "nunzio", "from": {"kind": "person", "label": "@self"}, "relation": "likes", "to": {"kind": "preference", "label": "caffè"}, "confidence": 700},
    {"op": "correct", "as": "nunzio", "correction": {"action": "assert", "from": {"kind": "person", "label": "@self"}, "relation": "lives_in", "to": {"kind": "place", "label": "Milano"}}},
    {"op": "relate", "as": "nunzio", "from": {"kind": "person", "label": "@self"}, "relation": "lives_in", "to": {"kind": "place", "label": "Torino"}, "confidence": 900},
    {"op": "correct", "as": "nunzio", "correction": {"action": "refute", "from": {"kind": "person", "label": "@self"}, "relation": "likes", "to": {"kind": "preference", "label": "caffè"}}},
    {"op": "relate", "as": "nunzio", "from": {"kind": "person", "label": "@self"}, "relation": "likes", "to": {"kind": "preference", "label": "caffè"}, "confidence": 900},
    {"op": "remember", "as": "nunzio", "kind": "object", "label": "chitarra"},
    {"op": "correct", "as": "nunzio", "correction": {"action": "remove", "node": {"kind": "object", "label": "chitarra"}}},
    {"op": "remember", "as": "nunzio", "kind": "object", "label": "chitarra"},
    {"op": "search", "as": "nunzio", "query": {"text": "carbonara"}},
    {"op": "search", "as": "nunzio", "query": {"text": "carbonaras", "depth": 0}},
    {"op": "search", "as": "nunzio", "query": {"text": "Giulia", "depth": 0}},
    {"op": "search", "as": "nunzio", "query": {"text": "Giulia", "depth": 2, "limit": 5}},
    {"op": "search", "as": "nunzio", "query": {"text": "vino", "household": True}},
    {"op": "search", "as": "nunzio", "query": {"text": "vino"}},
    {"op": "search", "as": "ospite", "query": {"text": "tisana", "household": True}},
    {"op": "search", "as": "nunzio", "query": {"text": "dove abito", "kinds": ["place"]}},
    {"op": "neighbors", "as": "nunzio", "query": {}},
    {"op": "neighbors", "as": "nunzio", "query": {"relation": "lives_in", "direction": "out"}},
    {"op": "neighbors", "as": "nunzio", "query": {"node": {"kind": "person", "label": "Giulia"}}},
    {"op": "neighbors", "as": "nunzio", "query": {"node": {"kind": "person", "label": "Nessuno"}}},
    {"op": "stats", "as": "nunzio"},
    {"op": "stats", "as": "anna"},
    {"op": "remember", "as": "nunzio", "kind": "place", "label": "Ro\u0000ma"},
    {"op": "remember", "as": "nunzio", "kind": "place", "label": "x", "origin": "user"},
    {"op": "remember", "as": "intruso", "kind": "place", "label": "x"},
    {"op": "relate", "as": "nunzio", "from": {"kind": "person", "label": "@self"}, "relation": "Bad Relation", "to": {"kind": "place", "label": "x"}},
    {"op": "stats", "as": "nunzio", "extra": 1},
    {"op": "search", "as": "nunzio", "query": {"text": "x", "limit": 0}},
    {"op": "register", "id": "anna", "name": "Anna", "role": "family", "consent": False},
    {"op": "search", "as": "anna", "query": {"text": "vino"}},
    {"op": "search", "as": "nunzio", "query": {"text": "vino", "household": True}},
    {"op": "erase", "as": "ospite", "confirm": "si"},
    {"op": "erase", "as": "ospite", "confirm": "ERASE:ospite"},
    {"op": "stats", "as": "ospite"},
]


def replay(engine) -> list:
    return [json.loads(engine.handle(json.dumps(step, ensure_ascii=False))) for step in SCENARIO]


class FallbackStandaloneTest(unittest.TestCase):
    def setUp(self):
        self.graph = PersonalGraph(PyGraph(lambda: 1_800_000_000_000))
        self.graph.register("nunzio", "Nunzio", "family")
        self.graph.register("ospite", "Ospite", "guest")

    def test_correction_prevails_and_blocks_automatic_facts(self):
        me = {"kind": "person", "label": "@self"}
        rome = {"kind": "place", "label": "Roma"}
        self.graph.correct("nunzio", {"action": "assert", "from": me, "relation": "lives_in", "to": rome})
        out = self.graph.call(
            "relate", **{"as": "nunzio", "from": me, "relation": "lives_in", "to": {"kind": "place", "label": "Torino"}, "confidence": 900}
        )
        self.assertEqual(out["change"], "blocked")

    def test_guest_is_isolated(self):
        self.graph.call("remember", **{"as": "ospite", "kind": "preference", "label": "tisana", "level": "public"})
        self.graph.call("remember", **{"as": "nunzio", "kind": "preference", "label": "tisana", "level": "public"})
        hits = self.graph.search("ospite", "tisana", household=True)
        self.assertTrue(hits)
        self.assertTrue(all(hit["owner"] == "ospite" for hit in hits))

    def test_secret_detail_fails_closed_without_encryption(self):
        with self.assertRaises(GraphError) as ctx:
            self.graph.call("remember", **{"as": "nunzio", "kind": "concept", "label": "pin", "detail": "1234", "level": "secret"})
        self.assertEqual(ctx.exception.code, "knowledge.seal")

    def test_erase_requires_confirmation_and_removes_everything(self):
        self.graph.call("remember", **{"as": "nunzio", "kind": "place", "label": "Roma"})
        with self.assertRaises(GraphError) as ctx:
            self.graph.call("erase", **{"as": "nunzio", "confirm": "si"})
        self.assertEqual(ctx.exception.code, "knowledge.confirm")
        self.assertEqual(self.graph.erase("nunzio")["receipt"]["nodes"], 1)
        with self.assertRaises(GraphError):
            self.graph.call("stats", **{"as": "nunzio"})

    def test_unsupported_operations_are_explicit(self):
        for op in ("extract", "persist", "consolidate"):
            with self.assertRaises(GraphError) as ctx:
                self.graph.call(op, **{"as": "nunzio"})
            self.assertEqual(ctx.exception.code, "knowledge.unsupported")

    def test_persistence_is_refused_without_native_engine(self):
        from personal_graph import create_engine

        if native_core.symbol("RustKnowledge") is None:
            with self.assertRaises(GraphError):
                create_engine(key=bytes(32), vault_dir="/tmp/nuxiva-never")


@unittest.skipIf(native_core.symbol("RustKnowledge") is None, "modulo nativo assente")
class NativeParityTest(unittest.TestCase):
    def test_primitives_match(self):
        normalize_native = native_core.symbol("knowledge_normalize")
        cosine_native = native_core.symbol("knowledge_cosine")
        for text in PRIMITIVE_CORPUS:
            with self.subTest(text=text[:40]):
                self.assertEqual(normalize_native(text), normalize(text))
        for a in PRIMITIVE_CORPUS:
            for b in PRIMITIVE_CORPUS:
                self.assertEqual(cosine_native(a, b), cosine_permille(embed(a), embed(b)), (a[:20], b[:20]))

    def test_decay_and_confidence_match(self):
        halve_native = native_core.symbol("knowledge_halve")
        noisy_native = native_core.symbol("knowledge_noisy_or")
        day = 86_400_000
        for value in (0, 1, 40, 700, 1000):
            for elapsed in (0, 1, day, 17 * day, 60 * day, 120 * day, 365 * day, 4000 * day):
                self.assertEqual(halve_native(value, elapsed, 120 * day), halve(value, elapsed, 120 * day))
        for a in range(0, 1001, 125):
            for b in range(0, 1001, 125):
                self.assertEqual(noisy_native(a, b), noisy_or(a, b))

    def test_scenario_replies_match(self):
        native = native_core.symbol("RustKnowledge")(bytes([1]) * 32, None, None, False)
        rust = replay(native)
        python = replay(PyGraph())
        for index, (a, b) in enumerate(zip(rust, python)):
            with self.subTest(step=index, op=SCENARIO[index]["op"]):
                self.assertEqual(a, b)


if __name__ == "__main__":
    unittest.main()
