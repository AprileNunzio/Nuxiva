from dataclasses import asdict, dataclass
import re
import time

from features.chat.reflex_memory import PersonaProfile, reflex_memory
from features.chat.words import word


@dataclass(frozen=True)
class ReflexResponse:
    reflex_text: str
    latency_ms: float
    kind: str
    needs_deep_reasoning: bool
    persona_applied: str

    def to_dict(self) -> dict:
        return asdict(self)


GREETING_PATTERNS = (
    r"\b(?:ciao|buongiorno|buonasera|salve|ehi|hey)\b",
    r"\b(?:come\s+va|tutto\s+bene|come\s+stai|che\s+si\s+dice)\b",
    r"\b(?:hello|hi|good\s+morning|how\s+are\s+you)\b",
    r"\b(?:hola|buenos\s+dias|buenas\s+tardes|que\s+tal)\b",
    r"\b(?:bonjour|salut|comment\s+ca\s+va)\b",
)

STATUS_PATTERNS = (
    r"\b(?:situazione|stato|come\s+siamo\s+messi|riassunto|panoramica)\b",
    r"\b(?:status|overview|summary)\b",
    r"\b(?:estado|resumen|situacion)\b",
)

REASONING_PATTERNS = (
    r"\b(?:perché|come\s+(?:fare|funziona|possiamo|risolvere|implementare)|progetta|sviluppa|analizza|risolvi|architettura|codice)\b",
    r"\b(?:why|how\s+(?:to|does|can|should)|design|develop|analyze|solve|refactor)\b",
    r"\b(?:por\s+que|como\s+(?:hacer|funciona|podemos)|disena|desarrolla|analiza)\b",
)


def _matches(patterns: tuple[str, ...], text: str) -> bool:
    for pat in patterns:
        if re.search(pat, text, re.IGNORECASE):
            return True
    return False


class AcousticReflexEngine:
    def __init__(self, memory_store=None) -> None:
        self.memory = memory_store or reflex_memory

    def evaluate(self, query: str, user_name: str = "Nunzio", lang: str = "it") -> ReflexResponse:
        start_time = time.monotonic()
        clean_q = query.strip()
        profile = self.memory.get_profile(user_name) or PersonaProfile(
            user_name=user_name,
            style="conversational",
            interests=["napoli_calcio", "devops"],
            facts={"favorite_team": "SSC Napoli"},
        )

        slots = {
            "name": profile.user_name,
            "focus": profile.facts.get("focus_today", "Nuxiva"),
            "fact": profile.facts.get("napoli_status", profile.facts.get("favorite_team", "")),
        }

        is_greeting = _matches(GREETING_PATTERNS, clean_q)
        is_status = _matches(STATUS_PATTERNS, clean_q)
        is_reasoning = _matches(REASONING_PATTERNS, clean_q)

        if is_greeting and not is_reasoning:
            kind = "greeting"
            needs_deep = False
            template_keys = self._select_greeting_keys(profile)
        elif is_status and not is_reasoning:
            kind = "quick_status"
            needs_deep = False
            template_keys = ["quick_status", "quick_status_optimal"]
        else:
            kind = "thinking_filler"
            needs_deep = True
            template_keys = ["thinking_filler_1", "thinking_filler_2", "thinking_filler_3", "thinking_filler_4"]

        rendered_options = [
            word(lang, "reflex", key).format(**slots)
            for key in template_keys
        ]
        chosen = self.memory.get_least_used(rendered_options) or rendered_options[0]
        self.memory.record_usage(chosen, kind)
        latency_ms = round((time.monotonic() - start_time) * 1000.0, 2)

        return ReflexResponse(
            reflex_text=chosen,
            latency_ms=latency_ms,
            kind=kind,
            needs_deep_reasoning=needs_deep,
            persona_applied=profile.style,
        )

    def _select_greeting_keys(self, profile: PersonaProfile) -> list[str]:
        if profile.style == "executive":
            return ["greeting_executive"]
        if "napoli_calcio" in profile.interests:
            return ["greeting_interest", "greeting_conversational"]
        return ["greeting_conversational"]


reflex_engine = AcousticReflexEngine()
