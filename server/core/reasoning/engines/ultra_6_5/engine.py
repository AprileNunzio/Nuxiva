from server.core.reasoning.engines.base import BaseReasoningEngine, Strategy
from server.features.llm_gateway.contracts import CognitiveEngineVersion

STRATEGY = Strategy(kind="deep", candidates=3, pick="best", critic=True, wait_s=15.0)


class UltraEngine(BaseReasoningEngine):
    @property
    def key(self) -> str:
        return "ultra"

    @property
    def version(self) -> CognitiveEngineVersion:
        return CognitiveEngineVersion.ULTRA_6_5

    @property
    def strategy(self) -> Strategy:
        return STRATEGY

    @property
    def icon(self) -> str:
        return "🔭"
