from server.core.reasoning.engines.base import BaseReasoningEngine, Strategy
from server.features.llm_gateway.contracts import CognitiveEngineVersion

STRATEGY = Strategy(kind="chat", candidates=2, pick="first", critic=False, wait_s=0.0)


class FastEngine(BaseReasoningEngine):
    @property
    def key(self) -> str:
        return "veloce"

    @property
    def version(self) -> CognitiveEngineVersion:
        return CognitiveEngineVersion.VELOCE_5_0

    @property
    def strategy(self) -> Strategy:
        return STRATEGY

    @property
    def icon(self) -> str:
        return "⚡"
