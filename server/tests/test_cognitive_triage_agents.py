import unittest
import asyncio
from server.features.cognitive_triage_agents.interfaces import (
    UserCognitiveInput,
    EmotionalState,
    RiskLevel,
    TriageMode
)
from server.features.cognitive_triage_agents.psychological_agent import PsychologicalAgent
from server.features.cognitive_triage_agents.methodological_agent import MethodologicalAgent
from server.features.cognitive_triage_agents.psychiatric_safety_agent import PsychiatricSafetyAgent
from server.features.cognitive_triage_agents.consensus_synthesizer import ConsensusSynthesizer
from server.features.cognitive_triage_agents.triage_service import CognitiveTriageService

class TestCognitiveTriageAgents(unittest.TestCase):
    def setUp(self) -> None:
        self.psych_agent = PsychologicalAgent()
        self.meth_agent = MethodologicalAgent()
        self.psychiatric_agent = PsychiatricSafetyAgent()
        self.synthesizer = ConsensusSynthesizer()
        self.service = CognitiveTriageService()

    def test_psychological_evaluation_calm(self) -> None:
        user_input = UserCognitiveInput(
            user_id="test_user",
            raw_text="Accendi la luce in salotto per favore.",
            vocal_jitter=0.01,
            hrv_ms=55.0,
            heart_rate_bpm=68.0,
            facial_valence=0.1
        )
        eval_res = self.psych_agent.evaluate(user_input)
        self.assertEqual(eval_res.emotional_state, EmotionalState.CALM)
        self.assertEqual(eval_res.cognitive_distortion, "none_detected")

    def test_psychological_evaluation_distortion_and_depression(self) -> None:
        user_input = UserCognitiveInput(
            user_id="test_user",
            raw_text="Tutto è perduto, mi sento vuoto e triste, non ha più senso nulla.",
            vocal_jitter=0.045,
            hrv_ms=22.0,
            heart_rate_bpm=98.0,
            facial_valence=-0.6
        )
        eval_res = self.psych_agent.evaluate(user_input)
        self.assertEqual(eval_res.emotional_state, EmotionalState.DEPRESSED)
        self.assertEqual(eval_res.cognitive_distortion, "catastrophizing")
        self.assertGreater(eval_res.empathy_depth, 0.5)

    def test_methodological_decomposition(self) -> None:
        user_input = UserCognitiveInput(
            user_id="test_user",
            raw_text="Non capisco più nulla, c'è troppo caos e mille cose da fare insieme, sono completamente bloccato.",
            gaze_stability=0.3,
            hrv_ms=25.0
        )
        eval_res = self.meth_agent.evaluate(user_input)
        self.assertGreater(eval_res.overload_index, 0.5)
        self.assertEqual(eval_res.cognitive_scaffolding, "single_variable_isolation")
        self.assertTrue(len(eval_res.socratic_steps) >= 2)

    def test_psychiatric_safety_interlock(self) -> None:
        user_input = UserCognitiveInput(
            user_id="test_user",
            raw_text="Voglio farla finita e togliermi la vita stasera.",
            heart_rate_bpm=120.0,
            hrv_ms=18.0
        )
        eval_res = self.psychiatric_agent.evaluate(user_input)
        self.assertEqual(eval_res.risk_level, RiskLevel.CRITICAL_EMERGENCY)
        self.assertTrue(eval_res.requires_interlock)
        self.assertTrue(eval_res.emergency_dispatch_required)
        self.assertIn("112", eval_res.emergency_helpline_payload.get("emergency_number", ""))

    def test_consensus_synthesis_safety_interlock(self) -> None:
        user_input = UserCognitiveInput(
            user_id="test_user",
            raw_text="Voglio uccidermi non ce la faccio più."
        )
        psych_res = self.psych_agent.evaluate(user_input)
        meth_res = self.meth_agent.evaluate(user_input)
        psychiatric_res = self.psychiatric_agent.evaluate(user_input)

        consensus = self.synthesizer.synthesize(user_input, psych_res, meth_res, psychiatric_res)
        self.assertEqual(consensus.mode, TriageMode.SAFETY_INTERLOCK)
        self.assertIsNotNone(consensus.response_override)
        self.assertTrue(consensus.emergency_alert_triggered)

    def test_consensus_synthesis_transparent_flow(self) -> None:
        user_input = UserCognitiveInput(
            user_id="test_user",
            raw_text="Mostrami il meteo per domani a Milano."
        )
        psych_res = self.psych_agent.evaluate(user_input)
        meth_res = self.meth_agent.evaluate(user_input)
        psychiatric_res = self.psychiatric_agent.evaluate(user_input)

        consensus = self.synthesizer.synthesize(user_input, psych_res, meth_res, psychiatric_res)
        self.assertEqual(consensus.mode, TriageMode.TRANSPARENT_COPROCESSOR)
        self.assertIsNone(consensus.response_override)
        self.assertFalse(consensus.emergency_alert_triggered)

    def test_service_async_evaluate_and_status(self) -> None:
        async def run_test() -> None:
            user_input = UserCognitiveInput(
                user_id="session_42",
                raw_text="Sono molto in ansia per il lavoro ma sto cercando di calmarmi.",
                vocal_jitter=0.03,
                hrv_ms=38.0
            )
            res = await self.service.evaluate_input(user_input)
            self.assertIn(res.mode, (TriageMode.ADAPTIVE_TONE, TriageMode.ON_DEMAND_COACHING))
            status = await self.service.get_status()
            self.assertEqual(status["total_evaluations"], 1)
            history = await self.service.get_history(5)
            self.assertEqual(len(history), 1)

        asyncio.run(run_test())

if __name__ == "__main__":
    unittest.main()
