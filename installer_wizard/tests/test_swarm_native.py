import json
import os
import unittest
from unittest import mock

from agenti.team import routing
from agenti.team.board import board
from agenti.team.scanner import scanner
from agenti.team.swarm import FLAG, Swarm, manifest_of, mode
from tests.test_ceo_routing_native import _corpus

try:
    import nuxiva_native
except ImportError:
    nuxiva_native = None

NATIVE = nuxiva_native is not None and hasattr(nuxiva_native, "RustSwarm")
LEARNED = {"medus": {"particles": 3}, "nuvol": {"weather": 9}}


@unittest.skipUnless(NATIVE, "nuxiva_native non disponibile")
class SwarmNativeTest(unittest.TestCase):
    def setUp(self):
        self.agents = scanner.scan()
        self.router = routing.Router(native=True)
        self.swarm = Swarm()

    def test_shadow_decisions_never_diverge_from_the_ceo(self):
        compared = 0
        for text in _corpus(self.agents):
            routed = self.router.decide(self.agents, text, LEARNED, 1)
            with self.subTest(text=text[:40]):
                outcome = self.swarm.shadow(self.agents, text, routed, LEARNED, 1)
                self.assertIsNot(outcome, False)
                compared += outcome is True
        self.assertGreater(compared, 100)
        self.assertEqual(self.swarm.stats["mismatched"], 0)

    def test_admission_builds_a_valid_plan_inside_the_budget(self):
        built = 0
        for text in _corpus(self.agents)[:120]:
            reply = self.swarm.admit(self.agents, text, LEARNED, 1)
            if reply is None or reply["kind"] != "task":
                continue
            task = reply["task"]
            with self.subTest(text=text[:40]):
                self.assertIn(reply["plan_error"], (None, "swarm.plan.no_planner", "swarm.graph.not_consulted", "swarm.plan.unknown_intent"))
                if reply["plan"] is None:
                    continue
                built += 1
                steps = reply["plan"]["steps"]
                self.assertEqual(steps[0]["worker_template"], reply["decision"]["primary"])
                self.assertLessEqual(sum(s["budget"]["tokens"] for s in steps), task["constraints"]["tokens_max"])
                self.assertLessEqual(sum(s["budget"]["tool_calls"] for s in steps), task["constraints"]["tool_calls_max"])
        self.assertGreater(built, 0)

    def _routable(self):
        for text in _corpus(self.agents):
            reply = self.swarm.admit(self.agents, text, LEARNED, 1)
            if reply and reply["kind"] == "task" and reply["plan"] and len(reply["plan"]["steps"]) == 1 \
                    and not reply["plan"]["steps"][0]["needs_graph"]:
                return reply
        self.fail("nessuna richiesta instradabile")

    def test_execution_goes_through_registered_handlers_and_posts_to_the_board(self):
        reply = self._routable()
        agent = reply["plan"]["steps"][0]["worker_template"]
        seen = []

        def handler(intent, goal, inputs):
            seen.append((intent, goal))
            return {"output": {"ok": True}, "evidence": ["prova.uno"]}

        self.swarm.register_handler(agent, handler)
        before = len(board.messages)
        report = self.swarm.execute(self.agents, reply)
        self.assertTrue(report["succeeded"])
        self.assertEqual(len(seen), 1)
        self.assertEqual(seen[0][0], reply["plan"]["steps"][0]["intent"])
        step = report["steps"][0]
        self.assertEqual(step["outcome"], "done")
        self.assertEqual(step["result"]["output"], {"ok": True})
        self.assertEqual(step["result"]["evidence"], ["prova.uno"])
        self.assertEqual(step["result"]["usage"]["tool_calls"], 1)
        self.assertGreater(len(board.messages), before)

    def test_agents_without_a_handler_fail_with_a_typed_error(self):
        reply = self._routable()
        report = self.swarm.execute(self.agents, reply)
        self.assertFalse(report["succeeded"])
        error = report["steps"][0]["error"]
        self.assertEqual(error["code"], "swarm.bridge.no_handler")
        self.assertEqual(error["kind"], "unavailable")

    def test_handler_exceptions_become_typed_errors(self):
        reply = self._routable()

        def broken(intent, goal, inputs):
            raise RuntimeError("guasto")

        self.swarm.register_handler(reply["plan"]["steps"][0]["worker_template"], broken)
        report = self.swarm.execute(self.agents, reply)
        self.assertEqual(report["steps"][0]["error"]["kind"], "internal")

    def test_invalid_input_is_rejected_not_executed(self):
        engine = self.swarm._engine_for(self.agents)
        with self.assertRaises(ValueError):
            engine.admit("ciao", "{}", 0)
        with self.assertRaises(ValueError):
            engine.admit("ciao", json.dumps({"id": "BAD ID", "input": "in.1", "risk_max": 1}), 0)
        with self.assertRaises(ValueError):
            engine.execute("{}", "{}", 0)
        with self.assertRaises(ValueError):
            engine.issue_graph_ref("zz", 0)

    def test_every_agent_has_a_manifest_the_swarm_accepts(self):
        for agent in self.agents.values():
            manifest = manifest_of(agent)
            self.assertEqual(manifest["id"], agent.id)
            self.assertIsInstance(manifest.get("worker", {}), dict)


class SwarmModeTest(unittest.TestCase):
    def test_mode_defaults_to_shadow_and_ignores_unknown_values(self):
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop(FLAG, None)
            self.assertEqual(mode(), "shadow")
        for raw, expected in (("python", "python"), ("RUST", "rust"), ("boh", "shadow"), ("", "shadow")):
            with mock.patch.dict(os.environ, {FLAG: raw}):
                self.assertEqual(mode(), expected)

    def test_python_mode_skips_the_comparison(self):
        with mock.patch.dict(os.environ, {FLAG: "python"}):
            self.assertIsNone(Swarm().shadow({}, "ciao", {}, {}))

    def test_without_native_the_swarm_stays_quiet(self):
        with mock.patch.dict(os.environ, {"NUXIVA_NATIVE": "0"}):
            swarm = Swarm()
        self.assertFalse(swarm.available)
        self.assertIsNone(swarm.admit({}, "ciao", {}))
        self.assertIsNone(swarm.shadow({}, "ciao", {"conversational": True}, {}))


if __name__ == "__main__":
    unittest.main()
