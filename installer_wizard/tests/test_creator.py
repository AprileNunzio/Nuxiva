import json
import time
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


class ShowKeepTest(unittest.TestCase):
    def setUp(self):
        import tempfile
        from pathlib import Path
        from agenti.particles import ParticleStore, show
        from state import store as state_store
        self.show, self.state_store = show, state_store
        self.store = ParticleStore(Path(tempfile.mkdtemp()) / "particles")
        patcher = mock.patch.object(show, "store", self.store)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.addCleanup(show.clear)
        saved = state_store.presence
        self.addCleanup(setattr, state_store, "presence", saved)
        show.refining.clear()
        mock.patch.object(show, "refine_later", lambda *a: False).start()
        self.addCleanup(mock.patch.stopall)

    def shown(self):
        with mock.patch.object(self.show, "_realistic_payload", lambda *a: None):
            return self.show.ensure_visual("mostrami come è fatto un cane")

    def test_dog_is_an_anatomy_with_named_parts_without_any_model(self):
        shown = self.shown()
        labels = [spot["label"] for spot in shown["hotspots"]]
        self.assertTrue(labels)
        self.assertFalse([name for name in labels if name.startswith("Elemento")])

    def test_old_stored_shape_is_replaced_by_the_anatomy(self):
        from agenti.particles import codec, morphogenesis
        old = morphogenesis.synthesize_spec("cane")
        key = self.show.concept_key("cane")
        self.store.put(key, old, codec.sample(old, 500, 1))
        self.store.index[key].pop("gen")
        entry = self.show.materialize_instant("cane")
        self.assertNotEqual(entry["spec"], old)
        self.assertEqual(self.store.lookup(key)["gen"], self.show.GENERATION)

    def test_figure_stays_while_someone_is_in_front_of_the_screen(self):
        self.shown()
        self.show.state["current"]["until"] = time.time() + 1
        self.state_store.presence = {"status": "ok", "people": [{"slug": "a"}]}
        time.sleep(1.1)
        self.assertIsNotNone(self.show.current())
        self.assertGreater(self.show.current()["remaining"], 60)

    def test_figure_goes_away_shortly_after_the_person_leaves(self):
        self.shown()
        self.state_store.presence = {"status": "ok", "people": []}
        self.show.state["current"]["seen"] = time.time() - self.show.LEAVE_GRACE - 1
        self.assertIsNone(self.show.current())

    def test_tick_clears_the_figure_and_wakes_the_page_when_the_person_left(self):
        self.shown()
        self.state_store.presence = {"status": "ok", "people": []}
        self.show.state["current"]["seen"] = time.time() - self.show.LEAVE_GRACE - 1
        self.show.tick()
        self.assertIsNone(self.show.state["current"])

    def test_tick_without_a_figure_does_nothing(self):
        self.show.clear()
        self.show.tick()

    def test_without_camera_the_long_fallback_applies(self):
        self.shown()
        self.state_store.presence = {"status": "offline", "people": []}
        self.assertGreater(self.show.current()["remaining"], 300)


class NetworkFailureTest(unittest.IsolatedAsyncioTestCase):
    async def test_answer_visual_survives_a_network_error_and_still_names_the_parts(self):
        import tempfile
        from pathlib import Path
        import httpx
        from agenti.particles import ParticleStore, show

        async def fake(*args, **kwargs):
            raise httpx.ConnectError("network error")

        store = ParticleStore(Path(tempfile.mkdtemp()) / "particles")
        with mock.patch.object(show, "store", store), mock.patch.object(show, "refine_later", lambda *a: False), \
                mock.patch.object(show, "_realistic_payload", lambda *a: None), mock.patch("agenti.brain.llm.generate", fake):
            answer = await show.answer_visual("mostrami come è fatto un cane", "it")
            show.clear()
        self.assertIsNotNone(answer)
        self.assertIn("Testa", answer["reply"])
        self.assertNotIn("Elemento", answer["reply"])

    async def test_design_and_brief_swallow_network_errors(self):
        import httpx

        async def fake(*args, **kwargs):
            raise httpx.ReadTimeout("lento")

        with mock.patch("agenti.brain.llm.generate", fake):
            self.assertEqual(await forma_creator.brief("cane"), "")
            self.assertIsNone(await forma_design.design("cane", None, ""))


if __name__ == "__main__":
    unittest.main()
