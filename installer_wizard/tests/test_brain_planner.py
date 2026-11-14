import asyncio
import json
import unittest
from unittest import mock

from agenti.chat import brain_engine
from agenti.mcpclient import brain, planner

PROMPT = {
    "task": {"id": "task-1", "intent": "lavoro"},
    "offers": [{"worker_template": "casa", "intents": ["lavoro"], "needs_graph": False, "tokens_max": 1000, "tool_calls_max": 4, "time_ms": 5000}],
    "attempt": 0,
    "rejected": None,
}


def plan(**over):
    step = {"id": "s1", "worker_template": "casa", "intent": "lavoro", "goal_ref": "g1", "needs_graph": False,
            "budget": {"tokens": 100, "tool_calls": 1, "time_ms": 1000}, "verify": "none"}
    step.update(over)
    return {"schema_version": 1, "id": "p1", "steps": [step], "edges": []}


class PlannerValidationTests(unittest.TestCase):
    def test_valid_plan_passes(self):
        self.assertEqual(planner.validate(plan(), PROMPT)["steps"][0]["id"], "s1")

    def test_rejections(self):
        bad = [
            plan(worker_template="altro"),
            plan(intent="altro"),
            plan(id="Bad Id"),
            plan(budget={"tokens": 10 ** 9, "tool_calls": 1, "time_ms": 1}),
            plan(budget={"tokens": 1, "tool_calls": True, "time_ms": 1}),
            plan(verify="boh"),
            plan(extra=1),
            {"steps": []},
            {**plan(), "unknown": 1},
            {**plan(), "edges": [{"from": "s1", "to": "zz"}]},
        ]
        for item in bad:
            with self.assertRaises(planner.PlanRejected, msg=str(item)):
                planner.validate(item, PROMPT)

    def test_step_limit(self):
        many = plan()
        many["steps"] = [{**many["steps"][0], "id": f"s{i}"} for i in range(planner.MAX_STEPS + 1)]
        with self.assertRaises(planner.PlanRejected):
            planner.validate(many, PROMPT)

    def test_duplicate_ids_are_rejected(self):
        twice = plan()
        twice["steps"].append(dict(twice["steps"][0]))
        with self.assertRaises(planner.PlanRejected):
            planner.validate(twice, PROMPT)

    def test_prompt_parsing_is_bounded(self):
        with self.assertRaises(planner.PlanRejected):
            planner.parse_prompt("x" * (planner.MAX_PROMPT_BYTES + 1))
        with self.assertRaises(planner.PlanRejected):
            planner.parse_prompt("[]")
        with self.assertRaises(ValueError):
            planner.parse_prompt("{")

    def test_make_runs_the_llm_on_the_loop_and_validates(self):
        async def run():
            loop = asyncio.get_running_loop()
            produced = json.dumps(plan())

            async def fake(prompt, **kwargs):
                self.assertTrue(kwargs["as_json"])
                return produced

            with mock.patch.object(planner, "generate", fake):
                call = planner.make(loop)
                return await asyncio.to_thread(call, json.dumps(PROMPT))

        self.assertEqual(json.loads(asyncio.run(run()))["id"], "p1")

    def test_make_rejects_hostile_llm_output(self):
        async def run():
            loop = asyncio.get_running_loop()

            async def fake(prompt, **kwargs):
                return {"steps": [{"id": "x"}]}

            with mock.patch.object(planner, "generate", fake):
                with self.assertRaises(planner.PlanRejected):
                    await asyncio.to_thread(planner.make(loop), json.dumps(PROMPT))

        asyncio.run(run())


class FallbackTests(unittest.TestCase):
    def run_attempt(self, outcome, enabled=True):
        async def go():
            with mock.patch.object(brain, "enabled", return_value=enabled), mock.patch.object(brain, "dispatch", return_value=outcome):
                return await brain.attempt("accendi", "nunzio", 1)
        return asyncio.run(go())

    def test_disabled_or_conversation_falls_back(self):
        self.assertIsNone(self.run_attempt({"kind": "executed"}, enabled=False))
        self.assertIsNone(self.run_attempt({"kind": "conversation"}))
        self.assertIsNone(self.run_attempt(None))
        self.assertIsNone(self.run_attempt({"kind": "rejected", "error": "x"}))

    def test_success_with_text_is_the_reply(self):
        got = self.run_attempt({"kind": "executed", "succeeded": True, "acted": True, "text": "fatto"})
        self.assertEqual(got["reply"], "fatto")
        self.assertEqual(got["intent"], "brain")

    def test_no_action_taken_falls_back(self):
        self.assertIsNone(self.run_attempt({"kind": "executed", "succeeded": False, "acted": False, "text": ""}))

    def test_failure_after_action_never_runs_twice(self):
        async def go():
            with mock.patch.object(brain, "enabled", return_value=True), mock.patch.object(
                    brain, "dispatch", return_value={"kind": "executed", "succeeded": False, "acted": True, "text": ""}):
                return await brain_engine.answer("accendi", "nunzio")
        got = asyncio.run(go())
        self.assertEqual(got["reply"], brain_engine.FAILED_REPLY)
        self.assertTrue(got["exact_reply"])

    def test_timeout_falls_back(self):
        async def go():
            def slow(*args):
                import time
                time.sleep(0.3)
                return {"kind": "conversation"}
            with mock.patch.object(brain, "enabled", return_value=True), mock.patch.object(brain, "dispatch", slow), mock.patch.object(brain, "TIMEOUT", 0.05):
                return await brain.attempt("x", "n", 1)
        self.assertIsNone(asyncio.run(go()))


if __name__ == "__main__":
    unittest.main()
