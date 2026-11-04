import asyncio
import time
from typing import List, Dict, Any
from .interfaces import (
    UserCognitiveInput,
    TriageConsensusResult
)
from .psychological_agent import PsychologicalAgent
from .methodological_agent import MethodologicalAgent
from .psychiatric_safety_agent import PsychiatricSafetyAgent
from .consensus_synthesizer import ConsensusSynthesizer

class CognitiveTriageService:
    def __init__(self) -> None:
        self._psychological = PsychologicalAgent()
        self._methodological = MethodologicalAgent()
        self._psychiatric = PsychiatricSafetyAgent()
        self._synthesizer = ConsensusSynthesizer()
        self._history: List[Dict[str, Any]] = []
        self._max_history = 50
        self._lock = asyncio.Lock()
        self._enabled = True

    @property
    def is_enabled(self) -> bool:
        return self._enabled

    def set_enabled(self, enabled: bool) -> None:
        self._enabled = enabled

    async def evaluate_input(self, user_input: UserCognitiveInput) -> TriageConsensusResult:
        if not self._enabled:
            return self._synthesizer.synthesize(
                user_input,
                self._psychological.evaluate(user_input),
                self._methodological.evaluate(user_input),
                self._psychiatric.evaluate(user_input)
            )

        loop = asyncio.get_running_loop()
        psych_task = loop.run_in_executor(None, self._psychological.evaluate, user_input)
        meth_task = loop.run_in_executor(None, self._methodological.evaluate, user_input)
        psychiatric_task = loop.run_in_executor(None, self._psychiatric.evaluate, user_input)

        psych_res, meth_res, psychiatric_res = await asyncio.gather(
            psych_task, meth_task, psychiatric_task
        )

        consensus = self._synthesizer.synthesize(
            user_input, psych_res, meth_res, psychiatric_res
        )

        await self._record_history(user_input.user_id, consensus)
        return consensus

    async def _record_history(self, user_id: str, consensus: TriageConsensusResult) -> None:
        async with self._lock:
            record = {
                "timestamp": time.time(),
                "user_id": user_id,
                "mode": consensus.mode.value,
                "speech_rate_factor": consensus.speech_rate_factor,
                "emotional_valence": consensus.emotional_valence,
                "emergency_alert_triggered": consensus.emergency_alert_triggered,
                "psychological": consensus.psychological_summary,
                "methodological": consensus.methodological_summary,
                "psychiatric": consensus.psychiatric_summary
            }
            self._history.append(record)
            if len(self._history) > self._max_history:
                self._history.pop(0)

    async def get_history(self, limit: int = 20) -> List[Dict[str, Any]]:
        async with self._lock:
            return list(reversed(self._history[-limit:]))

    async def get_status(self) -> Dict[str, Any]:
        async with self._lock:
            latest = self._history[-1] if self._history else None
            return {
                "service_enabled": self._enabled,
                "pipeline": "clinical_tri_agent_consensus",
                "agents": ["psychological_cbt", "methodological_socratic", "psychiatric_safety_gatekeeper"],
                "total_evaluations": len(self._history),
                "latest_evaluation": latest
            }

cognitive_triage_service = CognitiveTriageService()
