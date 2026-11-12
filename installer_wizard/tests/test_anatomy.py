import asyncio
import itertools
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from agenti.particles import codec, forma_anatomy, forma_design, forma_traits

try:
    import nuxiva_native
except ImportError:
    nuxiva_native = None

NATIVE = nuxiva_native is not None and hasattr(nuxiva_native, "forma_anatomy_sculpt")
CONCEPTS = ["cane", "gatto", "cavallo", "elefante", "giraffa", "coniglio", "orso", "drago", "uomo", "robot", "scimmia", "aquila", "anatra",
            "squalo", "pesce", "serpente", "ragno", "farfalla", "ape", "cervo", "topo", "mucca", "volpe", "leone"]
PHRASES = ["Mi mostri un cane", "i miei gatti", "una farfalla blu", "a shark", "an eagle", "una sedia", "catena", "", "gattopardo", "dogs and cats"]


def close(a, b) -> bool:
    if isinstance(a, dict):
        return a.keys() == b.keys() and all(close(a[k], b[k]) for k in a)
    if isinstance(a, list):
        return len(a) == len(b) and all(close(x, y) for x, y in zip(a, b))
    if isinstance(a, float) or isinstance(b, float):
        return abs(a - b) < 1e-7
    return a == b


def python_only(raw):
    with mock.patch.object(forma_anatomy, "_native", return_value=None):
        return forma_anatomy.sculpt(raw)


def python_preset(concept):
    with mock.patch.object(forma_anatomy, "_native", return_value=None):
        return forma_anatomy.preset(concept)


class AnatomyTest(unittest.TestCase):
    def test_every_known_concept_is_a_rich_valid_shape(self):
        for name in CONCEPTS:
            with self.subTest(name):
                found = python_preset(name)
                self.assertIsNotNone(found)
                spec = codec.validate(python_only(found))
                self.assertGreaterEqual(len(spec["parts"]), 12)
                self.assertLessEqual(len(spec["parts"]), codec.MAX_PARTS)
                self.assertEqual(codec.count(codec.sample(spec, 3000, 5)), 3000)

    def test_the_cat_names_its_anatomy(self):
        spec = python_only(python_preset("gatto"))
        names = [item["name"] for item in spec["labels"]]
        for want in ("head", "ears", "tail", "front_legs", "hind_legs", "body"):
            self.assertIn(want, names)
        self.assertEqual(len(names), len(set(names)))

    def test_unknown_concepts_and_hostile_input(self):
        self.assertIsNone(python_preset("una sedia"))
        self.assertIsNone(python_preset("catena"))
        with self.assertRaises(forma_anatomy.FormaError):
            forma_anatomy.normalize({"plan": "bird", "evil": 1})
        with self.assertRaises(forma_anatomy.FormaError):
            forma_anatomy.normalize({"plan": 4})
        wild = {"size": float("nan"), "legs": 1e9, "neck": -4, "pairs": 9999, "wings": float("inf"), "plan": "x"}
        self.assertTrue(python_only(wild)["parts"])

    def test_the_body_is_mirrored(self):
        found = {**python_preset("cane"), "tail_curl": 0.0}
        parts = python_only(found)["parts"]
        right = sum(p["at"][0] for p in parts if p["at"][0] > 0.05)
        left = sum(p["at"][0] for p in parts if p["at"][0] < -0.05)
        self.assertLess(abs(right + left), 0.05 * max(1.0, abs(right)))

    def test_proportions_change_the_silhouette(self):
        base = python_preset("cavallo")

        def height(spec):
            return max(p["at"][1] + p["size"][1] for p in spec["parts"]) - min(p["at"][1] - p["size"][1] for p in spec["parts"])

        self.assertGreater(height(python_only({**base, "legs": 2.2})), height(python_only({**base, "legs": 0.4})))

    def test_labels_become_named_hotspots(self):
        from agenti.particles.morphogenesis import extract_hotspots
        spec = codec.validate(python_only(python_preset("gatto")))
        spots = extract_hotspots("gatto", spec)
        labels = {spot["label"] for spot in spots}
        self.assertTrue({"Testa", "Orecchie", "Coda"} <= labels)
        self.assertFalse(any(label.startswith("Elemento") for label in labels))
        self.assertTrue(all(abs(v) <= 1.0 for spot in spots for v in spot["at"]))
        english = extract_hotspots("cat", spec, "en")
        self.assertIn("Tail", {spot["label"] for spot in english})

    def test_labels_survive_validation_and_are_sanitized(self):
        spec = {"parts": [{"shape": "sphere"}], "labels": [{"name": "head", "at": [0, 1, 0]}, {"name": "../x", "at": [0, 0, 0]}, "x"]}
        self.assertEqual(codec.validate(spec)["labels"], [{"name": "head", "at": [0.0, 1.0, 0.0]}])
        with self.assertRaises(codec.ParticleError):
            codec.validate({"parts": [{"shape": "sphere"}], "labels": [{"name": "head", "at": [99, 0, 0]}]})

    def test_part_names_exist_in_every_language(self):
        base = Path(forma_anatomy.__file__).parent / "language"
        keys = {}
        for lang in ("it", "en", "fr", "es"):
            keys[lang] = set(json.loads((base / f"{lang}.json").read_text(encoding="utf-8"))["parts"])
        self.assertEqual(len({frozenset(v) for v in keys.values()}), 1)
        used = {item["name"] for name in CONCEPTS for item in python_only(python_preset(name)).get("labels", [])}
        self.assertTrue(used <= keys["it"])

    @unittest.skipUnless(NATIVE, "native module not built")
    def test_rust_and_python_build_the_same_parts(self):
        for name in CONCEPTS:
            with self.subTest(name):
                found = python_preset(name)
                self.assertTrue(close(json.loads(nuxiva_native.forma_anatomy_sculpt(json.dumps(found))), python_only(found)))

    @unittest.skipUnless(NATIVE, "native module not built")
    def test_rust_and_python_agree_on_a_grid(self):
        grid = itertools.product(("quadruped", "biped", "bird", "fish", "insect", "serpent"), ("none", "point", "round", "floppy", "long"),
                                 (0.0, 1.5), (0.3, 2.0), (0, 2.2))
        for plan, ears, horns, build, wings in grid:
            raw = {"plan": plan, "ears": ears, "horns": horns, "build": build, "wings": wings, "pairs": 5, "tail_curl": -1.2}
            with self.subTest(raw=raw):
                self.assertTrue(close(json.loads(nuxiva_native.forma_anatomy_sculpt(json.dumps(raw))), python_only(raw)))

    @unittest.skipUnless(NATIVE, "native module not built")
    def test_rust_and_python_find_the_same_preset(self):
        for phrase in PHRASES + CONCEPTS:
            with self.subTest(phrase):
                native = forma_anatomy.preset(phrase)
                self.assertTrue(close(native, python_preset(phrase)) if native or python_preset(phrase) else True)
                self.assertEqual(native is None, python_preset(phrase) is None)

    @unittest.skipUnless(NATIVE, "native module not built")
    def test_rust_refuses_hostile_input(self):
        for raw in ('{"plan":"bird","evil":1}', "{", '{"size":"big"}', "x" * 70_000):
            with self.assertRaises(ValueError):
                nuxiva_native.forma_anatomy_sculpt(raw)
        with self.assertRaises(ValueError):
            nuxiva_native.forma_anatomy_preset("x" * 70_000)

    @unittest.skipUnless(NATIVE, "native module not built")
    def test_schema_is_shared(self):
        self.assertEqual(json.loads(nuxiva_native.forma_anatomy_schema()), forma_anatomy.SCHEMA)


class DesignTest(unittest.TestCase):
    def run_design(self, replies, start=None):
        calls = []

        async def generate(prompt, **kw):
            calls.append(prompt)
            reply = replies[min(len(calls), len(replies)) - 1]
            if isinstance(reply, Exception):
                raise reply
            return reply

        with mock.patch("agenti.brain.llm.generate", generate):
            return asyncio.run(forma_design.design("lupo", start)), calls

    def test_the_model_designs_then_reviews_an_anatomy(self):
        draft = {"anatomy": {"plan": "quadruped", "snout": 1.2, "ears": "point"}}
        better = {"anatomy": {"plan": "quadruped", "snout": 1.4, "ears": "point", "tail": 1.6}}
        spec, calls = self.run_design([draft, better])
        self.assertEqual(len(calls), 2)
        self.assertIn("<current>", calls[1])
        self.assertTrue(spec["labels"])
        self.assertEqual(spec, codec.validate(forma_anatomy.sculpt(better["anatomy"])))

    def test_a_draft_is_reviewed_once(self):
        spec, calls = self.run_design([{"anatomy": {"plan": "bird", "wings": 1.5}}], start=python_preset("aquila"))
        self.assertEqual(len(calls), 1)
        self.assertIn("<current>", calls[0])
        self.assertIsNotNone(spec)

    def test_traits_still_work_for_objects(self):
        spec, _ = self.run_design([{"traits": {"symmetry": "radial", "body": "bell"}}])
        self.assertTrue(spec["parts"])
        spec, _ = self.run_design([{"symmetry": "radial", "body": "bell"}])
        self.assertTrue(spec["parts"])

    def test_a_bad_review_keeps_the_first_design(self):
        first = {"anatomy": {"plan": "quadruped"}}
        spec, calls = self.run_design([first, {"anatomy": {"plan": "quadruped", "evil": 1}}])
        self.assertEqual(len(calls), 2)
        self.assertEqual(spec, codec.validate(forma_anatomy.sculpt(first["anatomy"])))

    def test_failures_give_none(self):
        self.assertIsNone(self.run_design([RuntimeError("x")])[0])
        self.assertIsNone(self.run_design([["not", "a", "dict"]])[0])
        self.assertIsNone(self.run_design([RuntimeError("x")], start=python_preset("aquila"))[0])

    def test_the_prompt_lists_both_schemas(self):
        text = forma_design.system()
        for item in forma_anatomy.SCHEMA["fields"] + forma_traits.SCHEMA["fields"]:
            self.assertIn(item["name"], text)


class VisualLaneTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        from agenti.particles import ParticleStore, show
        self.show = show
        self.store = ParticleStore(Path(tempfile.mkdtemp()) / "particles")
        patcher = mock.patch.object(show, "store", self.store)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.addCleanup(show.clear)
        show.refining.clear()

    async def test_a_cat_appears_at_once_with_named_parts(self):
        async def design(concept, start=None):
            return None

        with mock.patch("agenti.particles.forma_design.design", design):
            shown = self.show.ensure_visual("mostrami come è fatto un gatto")
        labels = {spot["label"] for spot in shown["hotspots"]}
        self.assertTrue({"Testa", "Orecchie", "Coda"} <= labels)
        self.assertGreaterEqual(len(self.store.lookup("gatto")["spec"]["parts"]), 12)

    async def test_the_chat_explains_instead_of_asking_to_repeat(self):
        async def generate(prompt, **kw):
            return "Il gatto ha un corpo agile, una testa piccola, orecchie a punta e una lunga coda."

        async def design(concept, start=None):
            return None

        with mock.patch("agenti.brain.llm.generate", generate), mock.patch("agenti.particles.forma_design.design", design):
            out = await self.show.answer_visual("mostrami come è fatto un gatto", "it")
        self.assertIn("orecchie", out["reply"])
        self.assertEqual(out["intent"], "visual")
        self.assertTrue(out["ui"]["particles"]["hotspots"])

    async def test_without_the_model_the_reply_lists_the_parts(self):
        async def generate(prompt, **kw):
            raise RuntimeError("down")

        with mock.patch("agenti.brain.llm.generate", generate):
            out = await self.show.answer_visual("fammi vedere un gatto", "it")
        self.assertIn("Testa", out["reply"])

    async def test_other_requests_are_left_alone(self):
        self.assertIsNone(await self.show.answer_visual("che ore sono", "it"))
        self.assertIsNone(await self.show.answer_visual("mostrami la mia password", "it"))

    def test_free_formulations_name_the_subject(self):
        from agenti.particles import extract_visual_concept
        for text in ("Disegnami un gatto", "fai vedere un gatto", "Che aspetto ha un gatto?", "come appare un gatto", "mostrami come è fatto un gatto",
                     "vorrei vedere un gatto"):
            with self.subTest(text):
                self.assertEqual(extract_visual_concept(text), "gatto")
