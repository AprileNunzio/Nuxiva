from typing import Any, Dict, List, Tuple

from server.core.reasoning.engines.base import BaseReasoningEngine, Strategy, stage
from server.features.llm_gateway.contracts import CognitiveEngineVersion

COMPLEXITY_WORDS = 45.0
FAST_NORADRENALINE = 0.75
FAST_COMPLEXITY = 0.3
EMPATHY_VALENCE = 0.65
COMPLEX = 0.65
RULES = (
    ("fast", CognitiveEngineVersion.VELOCE_5_0, {"noradrenaline_above": FAST_NORADRENALINE, "complexity_below": FAST_COMPLEXITY}),
    ("empathy", CognitiveEngineVersion.EMPATICO_5_0, {"abs_valence_above": EMPATHY_VALENCE}),
    ("complex", CognitiveEngineVersion.ULTRA_6_5, {"complexity_above": COMPLEX}),
    ("default", CognitiveEngineVersion.PRO_6_0, {}),
)


def complexity(query: str) -> float:
    return min(1.0, len(str(query or "").split()) / COMPLEXITY_WORDS)


def choose(query: str, limbic: Any) -> Tuple[str, CognitiveEngineVersion]:
    level = complexity(query)
    noradrenaline = float(getattr(limbic, "noradrenaline", 0.0))
    valence = float(getattr(limbic, "valence", 0.0))
    if noradrenaline > FAST_NORADRENALINE and level < FAST_COMPLEXITY:
        return "fast", CognitiveEngineVersion.VELOCE_5_0
    if abs(valence) > EMPATHY_VALENCE:
        return "empathy", CognitiveEngineVersion.EMPATICO_5_0
    if level > COMPLEX:
        return "complex", CognitiveEngineVersion.ULTRA_6_5
    return "default", CognitiveEngineVersion.PRO_6_0


def _engine(version: CognitiveEngineVersion) -> BaseReasoningEngine:
    from server.core.reasoning.engines.scanner import engine_scanner
    found = engine_scanner.get_engine(version.value)
    if found is None:
        raise LookupError(version.value)
    return found


class AutoEngine(BaseReasoningEngine):
    @property
    def key(self) -> str:
        return "auto"

    @property
    def version(self) -> CognitiveEngineVersion:
        return CognitiveEngineVersion.AUTO_6_5

    @property
    def strategy(self) -> Strategy:
        return _engine(CognitiveEngineVersion.PRO_6_0).strategy

    @property
    def icon(self) -> str:
        return "✨"

    @property
    def is_default(self) -> bool:
        return True

    def effective(self, query: str = "", limbic: Any = None) -> BaseReasoningEngine:
        return _engine(choose(query, limbic)[1])

    def route_stages(self, query: str, limbic: Any, lang: Any) -> List[Dict[str, Any]]:
        reason, version = choose(query, limbic)
        from server.core.reasoning.engines.base import text
        return [stage("router", "route", "route", lang, words=len(str(query or "").split()),
                      complexity=f"{complexity(query):.2f}", chosen=_engine(version).label(lang),
                      reason=text("stages", f"reason_{reason}", lang))]
