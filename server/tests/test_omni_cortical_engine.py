import unittest

from server.core.orchestrator.system1_router import System1Router
from server.core.reasoning.engines.base import Strategy
from server.core.reasoning.engines.scanner import EngineScanner
from server.features.brain.service import BrainEngineService
from server.features.llm_gateway.contracts import CognitiveEngineVersion

FICTION = ("JEPA", "TTT", "Friston", "MCTS", "Spiking", "Liquid", "1.58", "Thalamic", "GWT", "Coconut", "PRM")


class ReasoningEnginesTest(unittest.TestCase):
    def setUp(self) -> None:
        self.scanner = EngineScanner()
        self.service = BrainEngineService()

    def test_scanner_discovers_all_engines_with_real_strategies(self) -> None:
        engines = self.scanner.list_engines()
        self.assertEqual({e.version for e in engines}, set(CognitiveEngineVersion))
        for engine in engines:
            self.assertIsInstance(engine.strategy, Strategy)
            self.assertEqual(engine.vram_mb, 0)
            for lang in ("it", "en", "es", "fr"):
                words = engine.label(lang) + engine.summary(lang)
                for fake in FICTION:
                    self.assertNotIn(fake, words, (engine.key, lang))

    def test_flow_stages_describe_the_executed_strategy(self) -> None:
        fast = self.scanner.get_engine("veloce")
        stages = fast.get_flow_stages("ciao", {"ui_lang": "it"})
        self.assertEqual([s["kind"] for s in stages], ["reasoning", "decision"])
        auto = self.scanner.get_engine("auto")
        long_question = " ".join(["parola"] * 60)
        stages = auto.get_flow_stages(long_question, {"ui_lang": "en"})
        self.assertEqual(stages[0]["kind"], "router")
        self.assertIn("Nuxiva Ultra", stages[0]["detail"])
        self.assertIn("critic", [s["kind"] for s in stages])

    def test_service_switch(self) -> None:
        self.assertEqual(self.service.get_status().current_configured, CognitiveEngineVersion.AUTO_6_5)
        status = self.service.switch_engine(CognitiveEngineVersion.ULTRA_6_5)
        self.assertEqual(status.current_configured, CognitiveEngineVersion.ULTRA_6_5)
        ultra = next(e for e in status.engines if e.id == CognitiveEngineVersion.ULTRA_6_5)
        self.assertTrue(ultra.active)
        self.assertEqual(ultra.strategy.candidates, 3)

    def test_router_psi_formula(self) -> None:
        router = System1Router()
        low = router.calculate_neuro_cognitive_complexity_psi(task_complexity=0.1, semantic_surprise=0.1, user_emotion=0.1)
        self.assertEqual(router.select_engine(low), CognitiveEngineVersion.VELOCE_5_0)
        high = router.calculate_neuro_cognitive_complexity_psi(task_complexity=0.95, semantic_surprise=0.9, user_emotion=0.5)
        self.assertEqual(router.select_engine(high), CognitiveEngineVersion.ULTRA_6_5)


if __name__ == "__main__":
    unittest.main()
