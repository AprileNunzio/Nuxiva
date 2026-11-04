import unittest

from fastapi.testclient import TestClient

import nuxiva_supervisor
from features.chat.brain_chain import CONFIDENCE_WEIGHT, CRITIC_WEIGHT, HARD_TIMEOUT_S
from server.core.reasoning.engines.scanner import engine_scanner


class ReasoningExplainTest(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(nuxiva_supervisor.public)

    def test_strategy_comes_from_the_running_engine(self):
        data = self.client.get("/api/assistant/mode/explain", params={"mode": "nuxiva-6.0-pro"}).json()
        self.assertEqual(data["strategy"], engine_scanner.get_engine("pro").strategy.as_dict())
        self.assertEqual(data["routing"]["kind"], "deep")
        self.assertEqual(data["launched"], min(data["strategy"]["candidates"], data["routing"]["candidates"]))
        self.assertEqual(data["hard_timeout_s"], HARD_TIMEOUT_S)
        self.assertEqual((data["scoring"]["confidence_weight"], data["scoring"]["critic_weight"]), (CONFIDENCE_WEIGHT, CRITIC_WEIGHT))
        for word in ("JEPA", "TTT", "Friston", "MCTS", "Spiking", "Liquid", "1.58"):
            self.assertNotIn(word, data["name"] + data["summary"])

    def test_fast_mode_is_a_real_race_on_chat_models(self):
        data = self.client.get("/api/assistant/mode/explain", params={"mode": "nuxiva-5.0-fast"}).json()
        self.assertEqual(data["id"], "nuxiva-5.0-veloce")
        self.assertEqual(data["routing"]["kind"], "chat")
        self.assertEqual(data["strategy"]["pick"], "first")

    def test_auto_lists_its_rules_with_real_engines(self):
        data = self.client.get("/api/assistant/mode/explain", params={"mode": "nuxiva-6.5-auto"}).json()
        self.assertEqual([r["engine"]["id"] for r in data["auto_rules"]],
                         ["nuxiva-5.0-veloce", "nuxiva-5.0-empatico", "nuxiva-6.5-ultra", "nuxiva-6.0-pro"])
        for rule in data["auto_rules"]:
            self.assertEqual(rule["engine"]["strategy"], engine_scanner.get_engine(rule["engine"]["id"]).strategy.as_dict())

    def test_bad_and_unknown_modes(self):
        self.assertEqual(self.client.get("/api/assistant/mode/explain", params={"mode": "<x>"}).status_code, 400)
        self.assertEqual(self.client.get("/api/assistant/mode/explain", params={"mode": "nuxiva-9.9-nope"}).status_code, 404)


if __name__ == "__main__":
    unittest.main()
