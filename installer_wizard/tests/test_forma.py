import itertools
import json
import unittest
from unittest import mock

from agenti.particles import codec, forma, forma_traits

try:
    import nuxiva_native
except ImportError:
    nuxiva_native = None

NATIVE = nuxiva_native is not None and hasattr(nuxiva_native, "forma_sculpt")

ARCHETYPES = {
    "medusa": {"symmetry": "radial", "body": "bell", "length": 1.2, "width": 1.4, "limb": "hang", "limbs": 12, "limb_length": 1.8, "curl": 0.4,
               "theme": "bioluminescent"},
    "uccello": {"symmetry": "bilateral", "body": "spindle", "length": 2.0, "width": 0.5, "limb": "wing", "limbs": 2, "limb_length": 2.2,
                "theme": "fauna"},
    "atomo": {"symmetry": "orbital", "width": 1.0, "rings": 3, "theme": "microscopic"},
    "dna": {"symmetry": "spiral", "length": 3.0, "width": 0.7, "theme": "microscopic"},
    "colonna": {"symmetry": "axial", "body": "column", "length": 3.0, "width": 0.6, "rings": 4},
    "stella": {"symmetry": "radial", "body": "disc", "limb": "spoke", "limbs": 5, "limb_length": 1.4, "curl": -0.8},
}


def close(a, b, path="") -> bool:
    if isinstance(a, dict):
        return a.keys() == b.keys() and all(close(a[k], b[k], k) for k in a)
    if isinstance(a, list):
        return len(a) == len(b) and all(close(x, y) for x, y in zip(a, b))
    if isinstance(a, float) or isinstance(b, float):
        return abs(a - b) < 1e-7
    return a == b


def python_only(raw):
    with mock.patch.object(forma_traits, "_native", return_value=None):
        return forma_traits.sculpt(raw)


class FormaTest(unittest.TestCase):
    def test_every_archetype_is_a_valid_particle_spec(self):
        for name, raw in ARCHETYPES.items():
            with self.subTest(name):
                spec = python_only(raw)
                self.assertEqual(codec.validate(spec)["parts"][0]["shape"], spec["parts"][0]["shape"])
                blob = codec.sample(spec, 4000, 7)
                self.assertEqual(codec.count(blob), 4000)

    def test_same_traits_same_spec(self):
        self.assertEqual(python_only(ARCHETYPES["medusa"]), python_only(ARCHETYPES["medusa"]))

    def test_nonsense_traits_are_clamped(self):
        spec = python_only({"symmetry": "boh", "body": "boh", "length": 1e9, "width": -5, "limbs": 9999, "rings": 99, "curl": 9})
        self.assertTrue(1 <= len(spec["parts"]) <= forma.MAX_PARTS)

    def test_unknown_traits_and_hostile_plans_are_refused(self):
        with self.assertRaises(forma.FormaError):
            forma_traits.normalize({"colore": "rosso"})
        bad = [
            {"nodes": [{"op": "radial", "count": 9999, "child": {"op": "blob"}}]},
            {"nodes": [{"op": "radial", "count": 24, "child": {"op": "radial", "count": 24, "child": {"op": "blob"}}}]},
            {"nodes": [{"op": "lathe", "profile": [[1.0, 0.0]]}]},
            {"nodes": [{"op": "lathe", "profile": [[-1.0, 0.0], [1.0, 1.0]]}]},
            {"nodes": [{"op": "sweep", "dir": [0, 0, 0]}]},
            {"nodes": [{"op": "sweep", "steps": 999}]},
            {"nodes": [{"op": "blob", "at": [1e9, 0, 0]}]},
            {"nodes": [{"op": "blob", "x": 1}]},
            {"nodes": []},
            {"nodes": [], "extra": 1},
        ]
        for plan in bad:
            with self.subTest(plan=plan), self.assertRaises(forma.FormaError):
                forma.compile_plan(plan)

    def test_radial_and_bilateral_symmetry(self):
        medusa = python_only(ARCHETYPES["medusa"])["parts"]
        self.assertGreaterEqual(len([p for p in medusa if p["at"][1] < -0.8]), 12)
        self.assertLess(abs(sum(p["at"][0] for p in medusa if p["at"][1] < -1.2)), 0.5)
        bird = python_only(ARCHETYPES["uccello"])["parts"]
        right = sum(p["at"][0] for p in bird if p["at"][0] > 0.3)
        left = sum(p["at"][0] for p in bird if p["at"][0] < -0.3)
        self.assertGreater(right, 0)
        self.assertAlmostEqual(right + left, 0.0, places=6)

    def test_schema_matches_the_defaults(self):
        self.assertEqual(sorted(f["name"] for f in forma_traits.SCHEMA["fields"]), sorted(forma_traits.DEFAULTS))


@unittest.skipUnless(NATIVE, "nuxiva_native non disponibile")
class FormaNativeTest(unittest.TestCase):
    def test_rust_and_python_build_the_same_parts(self):
        for name, raw in ARCHETYPES.items():
            with self.subTest(name):
                self.assertTrue(close(json.loads(nuxiva_native.forma_sculpt(json.dumps(raw))), python_only(raw)))

    def test_rust_and_python_agree_on_a_grid_of_traits(self):
        grid = itertools.product(("radial", "bilateral", "axial", "spiral", "orbital"), ("dome", "bell", "spindle", "sphere", "column", "disc", "cone"),
                                 ("hang", "spread", "reach", "spoke", "wing"), (0, 1, 7, 24), (-1.5, 0.0, 0.7))
        for symmetry, body, limb, limbs, curl in grid:
            raw = {"symmetry": symmetry, "body": body, "limb": limb, "limbs": limbs, "curl": curl, "rings": limbs % 5, "length": 2.2, "width": 0.9}
            with self.subTest(**raw):
                self.assertTrue(close(json.loads(nuxiva_native.forma_sculpt(json.dumps(raw))), python_only(raw)))

    def test_schema_is_shared(self):
        self.assertEqual(json.loads(nuxiva_native.forma_schema()), forma_traits.SCHEMA)

    def test_rust_refuses_hostile_input(self):
        for raw in ("{", '{"extra":1}', '{"limbs":-1}', "x" * 70000):
            with self.subTest(raw=raw[:12]), self.assertRaises(ValueError):
                nuxiva_native.forma_sculpt(raw)
        for raw in ('{"nodes":[{"op":"blob","at":[1e9,0,0]}]}', '{"nodes":[{"op":"radial","count":9999,"child":{"op":"blob"}}]}', '{"nodes":[]}'):
            with self.subTest(raw=raw[:30]), self.assertRaises(ValueError):
                nuxiva_native.forma_compile(raw)

    def test_the_bridge_prefers_rust(self):
        self.assertTrue(close(forma_traits.sculpt(ARCHETYPES["dna"]), python_only(ARCHETYPES["dna"])))



class FormaDesignTest(unittest.TestCase):
    def run_design(self, answer):
        import asyncio
        from agenti.particles import forma_design

        async def fake(*args, **kwargs):
            if isinstance(answer, Exception):
                raise answer
            return answer

        with mock.patch("agenti.brain.llm.generate", fake):
            return asyncio.run(forma_design.design("medusa"))

    def test_model_answer_becomes_a_valid_spec(self):
        spec = self.run_design({**ARCHETYPES["medusa"], "colore": "rosso", "ignora": "tutto"})
        self.assertIsNotNone(spec)
        self.assertEqual(spec, codec.validate(spec))

    def test_bad_answers_fall_back_to_none(self):
        for answer in ("testo", None, ["a"], {"limbs": "molti", "length": "lungo"}, RuntimeError("giù")):
            with self.subTest(answer=str(answer)[:20]):
                result = self.run_design(answer)
                if isinstance(answer, dict):
                    self.assertIsNotNone(result)
                else:
                    self.assertIsNone(result)

    def test_prompt_lists_every_field(self):
        from agenti.particles import forma_design
        text = forma_design.system()
        for field in forma_traits.DEFAULTS:
            self.assertIn(field, text)


if __name__ == "__main__":
    unittest.main()
