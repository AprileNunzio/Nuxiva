from server.core.reasoning.engines.base import BaseReasoningEngine, Strategy
from server.features.llm_gateway.contracts import CognitiveEngineVersion

STRATEGY = Strategy(kind="deep", candidates=2, pick="best", critic=True, wait_s=6.0)


class ProEngine(BaseReasoningEngine):
    @property
    def key(self) -> str:
        return "pro"

    @property
    def version(self) -> CognitiveEngineVersion:
        return CognitiveEngineVersion.PRO_6_0

    @property
    def strategy(self) -> Strategy:
        return STRATEGY

    @property
    def icon(self) -> str:
        return "🧠"
