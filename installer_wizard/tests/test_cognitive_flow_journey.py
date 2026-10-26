import sys
import unittest
from pathlib import Path
from unittest.mock import patch, AsyncMock

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from features.brain.journey import journeys
from features.brain import stages
from features.chat.journey_flow import ChatJourney
from features.chat import brain_chain
from server.core.reasoning.engines.scanner import engine_scanner

class CognitiveFlowJourneyTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        journeys._items.clear()
        journeys.seq = 0

    async def test_all_scanned_engines_emit_correct_stages(self):
        self.assertGreaterEqual(len(engine_scanner.list_engines()), 6)

        for engine in [engine_scanner.get_default_engine()]:
            journeys._items.clear()
            
            flow = ChatJourney("spiegami la meccanica quantistica", "spiegami la meccanica quantistica", "kiosk", "utente")
            flow.begin()
            
            dummy_local = AsyncMock(return_value={"agent_id": engine.name, "speech_output": "Risposta completata con successo."})
            route = {
                "kind": "chat" if engine.latency_sla_ms <= 50 else "deep",
                "reason": f"test {engine.name}",
                "models": ["local:granite3.3"],
                "max_tokens": 1024,
            }
            context = {}

            with patch.object(brain_chain, "_run_candidate", AsyncMock(return_value={"agent_id": engine.name, "speech_output": "Test reply"})):
                async with stages.stage("system2", "Generazione della risposta"):
                    res = await brain_chain.ask("spiegami la meccanica quantistica", "kiosk", context, route, dummy_local)

            flow.answered({"reply": res.get("speech_output", ""), "agent": engine.name, "intent": "conversation"})

            snap = journeys.snapshot()
            self.assertEqual(len(snap["journeys"]), 1)
            j = snap["journeys"][0]
            node_kinds = [n["k"] for n in j["nodes"]]
            
            self.assertIn("input", node_kinds)
            self.assertIn("laws", node_kinds)
            self.assertIn("cache", node_kinds)
            self.assertIn("system2", node_kinds)
            self.assertIn("answer", node_kinds)

            flow_stages = engine.get_flow_stages("spiegami la meccanica quantistica", context)
            for st in flow_stages:
                self.assertIn(st["kind"], node_kinds, f"Stage {st['kind']} missing for engine {engine.name}")
                matching_node = next((n for n in j["nodes"] if n["n"] == st["name"]), None)
                self.assertIsNotNone(matching_node, f"Node {st['name']} missing for engine {engine.name}")

            edges = j["edges"]
            self.assertGreater(len(edges), len(flow_stages))
            self.assertEqual(j["state"], "done")

if __name__ == "__main__":
    unittest.main()
