import json
import unittest
from unittest import mock

from agenti.particles import forma_creator, forma_design, forma_inspect

try:
    import nuxiva_native
except ImportError:
    nuxiva_native = None

NATIVE = nuxiva_native is not None and hasattr(nuxiva_native, "forma_inspect")

def blob(shape, at, size):
    return {"op": "blob", "shape": shape, "at": at, "size": size}


def joined():
    return {"nodes": [blob("box", [0, 0, 0], [1, 0.5, 2]), blob("cylinder", [1.1, -0.5, 1], [0.4, 0.1, 0.4]),
                      blob("cylinder", [0, 0.8, 1.5], [0.15, 0.4, 0.15]), blob("sphere", [0, 0.2, -2.2], [0.3, 0.3, 0.3]),
                      blob("box", [0, 0.4, 0.2], [0.5, 0.3, 0.5])]}


def apart():
    return {"nodes": [blob("box", [0, 0, 0], [1, 0.5, 2]), blob("sphere", [6, 0, 0], [0.3, 0.3, 0.3]),
                      blob("sphere", [-6, 2, 0], [0.3, 0.3, 0.3]), blob("box", [0, 0.4, 0.2], [0.5, 0.3, 0.5]),
                      blob("box", [0, 0.4, 1.2], [0.5, 0.3, 0.5])]}


class InspectTest(unittest.TestCase):
    def report(self, tree):
        with mock.patch.object(forma_inspect, "_native", return_value=None):
            return forma_inspect.inspect(tree)

    def test_connected_object_has_no_detached_parts(self):
        self.assertNotIn("detached_parts", self.report(joined())["issues"])

    def test_floating_part_is_reported_with_its_place(self):
        found = self.report(apart())
        self.assertIn("detached_parts", found["issues"])
        self.assertEqual(len(found["loose"]), 2)

    def test_feedback_is_bounded_json(self):
        text = forma_creator.feedback(self.report(apart()))
        self.assertLessEqual(len(text), forma_creator.MAX_TEXT)
        json.loads(text)

    @unittest.skipUnless(NATIVE, "native wheel missing")
    def test_native_and_python_agree(self):
        for payload in (joined(), apart()):
            native = json.loads(nuxiva_native.forma_inspect(json.dumps(payload)))
            with mock.patch.object(forma_inspect, "_native", return_value=None):
                python = forma_inspect.inspect(payload)
            self.assertEqual(native["issues"], python["issues"])
            self.assertEqual(native["components"], python["components"])
            self.assertAlmostEqual(native["asymmetry"], python["asymmetry"], places=6)


class CreatorTest(unittest.IsolatedAsyncioTestCase):
    async def test_brief_is_clipped_and_wrapped_as_data(self):
        seen = {}

        async def fake(prompt, **kwargs):
            seen["prompt"] = prompt
            return {"kind": "x" * 5000}

        with mock.patch("agenti.brain.llm.generate", fake):
            text = await forma_creator.brief("locomotiva", "aiuto")
        self.assertIn("<object>locomotiva</object>", seen["prompt"])
        self.assertIn("<advice>aiuto</advice>", seen["prompt"])
        self.assertLessEqual(len(text), forma_creator.MAX_TEXT)

    async def test_brief_survives_a_failing_model(self):
        async def fake(*args, **kwargs):
            raise RuntimeError("giù")

        with mock.patch("agenti.brain.llm.generate", fake):
            self.assertEqual(await forma_creator.brief("locomotiva"), "")

    async def test_advice_without_experts_is_empty(self):
        with mock.patch("agenti.experts.routing.choose", return_value=None):
            self.assertEqual(await forma_creator.advice("locomotiva"), "")

    async def test_create_passes_the_knowledge_to_the_design(self):
        async def knowledge(concept):
            return "scheda"

        async def design(concept, start=None, context=""):
            return {"context": context}

        with mock.patch.object(forma_creator, "knowledge", knowledge), mock.patch.object(forma_design, "design", design):
            self.assertEqual(await forma_design.create("treno"), {"context": "scheda"})


class DesignLoopTest(unittest.IsolatedAsyncioTestCase):
    async def run_loop(self, answers, start=None):
        prompts = []
        queue = list(answers)

        async def fake(prompt, **kwargs):
            prompts.append(prompt)
            return queue.pop(0)

        with mock.patch("agenti.brain.llm.generate", fake):
            result = await forma_design.design("locomotiva", start, "scheda")
        return result, prompts

    async def test_report_is_fed_back_and_the_loop_stops_when_clean(self):
        broken = {"plan": apart()}
        fixed = {"plan": joined()}
        result, prompts = await self.run_loop([broken, fixed, fixed])
        self.assertIsNotNone(result)
        self.assertIn("<brief>scheda</brief>", prompts[0])
        self.assertIn("<report>", prompts[1])
        self.assertEqual(len(prompts), 2)

    async def test_failure_keeps_what_was_built(self):
        good = {"plan": joined()}
        queue = [good, RuntimeError("giù")]

        async def fake(prompt, **kwargs):
            item = queue.pop(0)
            if isinstance(item, Exception):
                raise item
            return item

        with mock.patch("agenti.brain.llm.generate", fake):
            self.assertIsNotNone(await forma_design.design("locomotiva", None, ""))

    async def test_refinement_runs_a_single_pass(self):
        start = {"plan": joined()}
        _, prompts = await self.run_loop([start], start)
        self.assertEqual(len(prompts), 1)


if __name__ == "__main__":
    unittest.main()
