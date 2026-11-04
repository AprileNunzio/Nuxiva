from server.core.reasoning.engines.base import BaseReasoningEngine, Strategy
from server.features.llm_gateway.contracts import CognitiveEngineVersion

STRATEGY = Strategy(kind="deep", candidates=1, pick="sequential", critic=False, wait_s=0.0)


class ClassicEngine(BaseReasoningEngine):
    @property
    def key(self) -> str:
        return "classico"

    @property
    def version(self) -> CognitiveEngineVersion:
        return CognitiveEngineVersion.LEGACY_4_2

    @property
    def strategy(self) -> Strategy:
        return STRATEGY

    @property
    def icon(self) -> str:
        return "📜"
