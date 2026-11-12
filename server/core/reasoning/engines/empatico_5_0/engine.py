from server.core.reasoning.engines.base import BaseReasoningEngine, Strategy
from server.features.llm_gateway.contracts import CognitiveEngineVersion

STRATEGY = Strategy(kind="deep", candidates=2, pick="best", critic=True, wait_s=4.0)


class EmpathicEngine(BaseReasoningEngine):
    @property
    def key(self) -> str:
        return "empatico"

    @property
    def version(self) -> CognitiveEngineVersion:
        return CognitiveEngineVersion.EMPATICO_5_0

    @property
    def strategy(self) -> Strategy:
        return STRATEGY

    @property
    def icon(self) -> str:
        return "💗"
