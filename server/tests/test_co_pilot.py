import unittest
from server.core.memory.fast_memory import FastMemoryBridge
from server.core.orchestrator.co_pilot import LiveCoPilotBridge


class TestFastMemoryAndCoPilot(unittest.TestCase):
    def test_fast_memory_exact_and_similarity(self) -> None:
        memory = FastMemoryBridge(max_capacity=4)
        memory.insert("cmd.nav.home", [1.0, 0.0, 0.0], "resp.nav.home_ok")
        memory.insert("cmd.nav.settings", [0.0, 1.0, 0.0], "resp.nav.settings_ok")

        self.assertEqual(len(memory), 2)

        hit_exact = memory.lookup("cmd.nav.home")
        self.assertIsNotNone(hit_exact)
        self.assertEqual(hit_exact.response_key, "resp.nav.home_ok")
        self.assertEqual(hit_exact.similarity, 1.0)
        self.assertEqual(hit_exact.hit_count, 1)

        hit_sim = memory.lookup("cmd.nav.unknown", [0.98, 0.02, 0.0], similarity_threshold=0.8)
        self.assertIsNotNone(hit_sim)
        self.assertEqual(hit_sim.response_key, "resp.nav.home_ok")
        self.assertGreater(hit_sim.similarity, 0.8)

        miss = memory.lookup("cmd.nav.unknown", [0.0, 0.0, 1.0], similarity_threshold=0.8)
        self.assertIsNone(miss)

    def test_fast_memory_lru_prune(self) -> None:
        memory = FastMemoryBridge(max_capacity=2)
        memory.insert("k1", [1.0], "r1")
        memory.insert("k2", [2.0], "r2")
        self.assertEqual(len(memory), 2)

        memory.lookup("k1")
        memory.insert("k3", [3.0], "r3")
        self.assertEqual(len(memory), 2)

        self.assertIsNotNone(memory.lookup("k1"))
        self.assertIsNotNone(memory.lookup("k3"))
        self.assertIsNone(memory.lookup("k2"))

    def test_live_copilot_session_lifecycle(self) -> None:
        copilot = LiveCoPilotBridge()
        self.assertFalse(copilot.is_live())

        act_start = copilot.start_session("chess", "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR")
        self.assertTrue(copilot.is_live())
        self.assertEqual(act_start.insight_key, "copilot.game_started")
        self.assertEqual(act_start.target_morphology, "FloatingOrb")

        m1 = copilot.on_move_applied("e2e4", "board_state_1")
        self.assertEqual(m1.insight_key, "copilot.opening_acknowledged")
        self.assertEqual(m1.suggested_move, "e2e4")

        m2 = copilot.on_move_applied("e7e5", "board_state_2")
        self.assertEqual(m2.insight_key, "copilot.opening_acknowledged")

        m3 = copilot.on_move_applied("g1f3", "board_state_3")
        self.assertEqual(m3.action_kind, "SuggestMove")
        self.assertEqual(m3.insight_key, "copilot.tactical_suggestion")

        act_end = copilot.end_session()
        self.assertFalse(copilot.is_live())
        self.assertEqual(act_end.insight_key, "copilot.game_ended")
        self.assertEqual(act_end.target_morphology, "CoreHero")


if __name__ == "__main__":
    unittest.main()
