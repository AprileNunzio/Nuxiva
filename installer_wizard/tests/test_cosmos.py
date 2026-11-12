import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from agenti.particles import codec, forma_anatomy, forma_cosmos, forma_design
from tests.test_anatomy import close

try:
    import nuxiva_native
except ImportError:
    nuxiva_native = None

NATIVE = nuxiva_native is not None and hasattr(nuxiva_native, "forma_cosmos_sculpt")
CONCEPTS = ["una galassia", "la via lattea", "un buco nero", "una nebulosa", "il sistema solare", "una stella", "il sole", "saturno", "giove",
            "nettuno", "marte", "la terra", "un pianeta", "a galaxy", "black hole"]


def python_only(raw):
    with mock.patch.object(forma_cosmos, "_native", return_value=None):
        return forma_cosmos.sculpt(raw)


def python_preset(concept):
    with mock.patch.object(forma_cosmos, "_native", return_value=None):
        return forma_cosmos.preset(concept)


class CosmosTest(unittest.TestCase):
    def test_every_celestial_concept_is_a_named_valid_shape(self):
        for name in CONCEPTS:
            with self.subTest(name):
                found = python_preset(name)
                self.assertIsNotNone(found)
                spec = codec.validate(python_only(found))
                self.assertTrue(2 <= len(spec["parts"]) <= codec.MAX_PARTS)
                self.assertTrue(spec["labels"])
                self.assertEqual(codec.count(codec.sample(spec, 3000, 5)), 3000)

    def test_the_right_kind_is_chosen(self):
        for phrase, kind in (("una galassia a spirale", "galaxy"), ("un buco nero", "blackhole"), ("saturno e i suoi anelli", "planet"),
                             ("il sistema solare", "system"), ("la nebulosa di orione", "nebula"), ("una stella", "star")):
            self.assertEqual(python_preset(phrase)["kind"], kind, phrase)
        self.assertIsNone(python_preset("una sedia"))

    def test_a_galaxy_gets_one_part_per_arm(self):
        count = lambda arms: len(python_only({"kind": "galaxy", "arms": arms})["parts"])  # noqa: E731
        self.assertEqual(count(4) - count(2), 2)

    def test_the_new_shapes_are_diffuse_and_inside_the_unit_box(self):
        for shape in ("cloud", "disc", "spiral", "ring", "halo", "orbit"):
            spec = {"parts": [{"shape": shape}]}
            blob = codec.sample(spec, 2000, 3)
            self.assertEqual(codec.count(blob), 2000)

    def test_hostile_input_is_refused_or_clamped(self):
        with self.assertRaises(forma_cosmos.FormaError):
            forma_cosmos.normalize({"kind": "star", "evil": 1})
        wild = {"kind": "x", "size": float("nan"), "tilt": 1e9, "arms": 99, "rings": 99, "moons": 99, "planets": 0, "bands": 99, "glow": -3}
        self.assertTrue(python_only(wild)["parts"])

    def test_celestial_labels_are_hotspots_in_every_language(self):
        from agenti.particles.morphogenesis import extract_hotspots
        spec = codec.validate(python_only(python_preset("saturno")))
        names = {spot["label"] for spot in extract_hotspots("saturno", spec)}
        self.assertTrue({"Anelli", "Fasce"} <= names)
        self.assertIn("Rings", {spot["label"] for spot in extract_hotspots("saturn", spec, "en")})
        base = Path(forma_anatomy.__file__).parent / "language"
        parts = {lang: set(json.loads((base / f"{lang}.json").read_text(encoding="utf-8"))["parts"]) for lang in ("it", "en", "fr", "es")}
        self.assertEqual(len({frozenset(v) for v in parts.values()}), 1)
        for concept in CONCEPTS:
            used = {item["name"] for item in python_only(python_preset(concept))["labels"]}
            self.assertTrue(used <= parts["it"], concept)

    @unittest.skipUnless(NATIVE, "native module not built")
    def test_rust_and_python_agree(self):
        for concept in CONCEPTS:
            with self.subTest(concept):
                found = python_preset(concept)
                self.assertTrue(close(json.loads(nuxiva_native.forma_cosmos_sculpt(json.dumps(found))), python_only(found)))
                self.assertEqual(forma_cosmos.preset(concept), found)
        for kind in ("galaxy", "star", "planet", "nebula", "blackhole", "system"):
            for tilt, arms, rings, bands in ((0.0, 1, 0, 0), (45.0, 6, 4, 8), (-80.0, 3, 2, 1)):
                raw = {"kind": kind, "tilt": tilt, "arms": arms, "rings": rings, "bands": bands, "moons": 3, "planets": 7, "glow": 1.7}
                self.assertTrue(close(json.loads(nuxiva_native.forma_cosmos_sculpt(json.dumps(raw))), python_only(raw)), raw)

    @unittest.skipUnless(NATIVE, "native module not built")
    def test_rust_refuses_hostile_input_and_shares_the_schema(self):
        for raw in ('{"kind":"star","evil":1}', "{", '{"size":"big"}', "x" * 70_000):
            with self.assertRaises(ValueError):
                nuxiva_native.forma_cosmos_sculpt(raw)
        self.assertEqual(json.loads(nuxiva_native.forma_cosmos_schema()), forma_cosmos.SCHEMA)

    @unittest.skipUnless(NATIVE, "native module not built")
    def test_new_shapes_sample_the_same_in_rust_and_python(self):
        from agenti.particles import codec as c
        for shape in ("cloud", "disc", "spiral", "ring", "halo", "orbit"):
            spec = {"parts": [{"shape": shape, "size": [1.0, 0.5, 1.2], "rot": [10.0, 20.0, 30.0]}]}
            self.assertEqual(c.sample(spec, 3000, 9), c.sample_python(spec, 3000, 9), shape)


class CosmosDesignTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        from agenti.particles import ParticleStore, show
        self.show = show
        self.store = ParticleStore(Path(tempfile.mkdtemp()) / "particles")
        patcher = mock.patch.object(show, "store", self.store)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.addCleanup(show.clear)

    def test_the_model_can_answer_with_a_cosmos(self):
        spec, kept = forma_design.build({"cosmos": {"kind": "galaxy", "arms": 3, "evil": 1}})
        self.assertEqual(kept, {"cosmos": {"kind": "galaxy", "arms": 3}})
        self.assertTrue(spec["labels"])
        self.assertIn("cosmos", forma_design.system())

    def test_a_draft_exists_for_creatures_and_stars_only(self):
        self.assertIn("anatomy", forma_design.draft("gatto"))
        self.assertIn("cosmos", forma_design.draft("galassia"))
        self.assertIsNone(forma_design.draft("treno"))

    async def test_a_galaxy_appears_at_once_with_named_parts(self):
        async def design(concept, start=None):
            return None

        with mock.patch("agenti.particles.forma_design.design", design):
            shown = self.show.ensure_visual("mostrami una galassia")
        labels = {spot["label"] for spot in shown["hotspots"]}
        self.assertTrue({"Nucleo", "Bracci a spirale"} <= labels)
