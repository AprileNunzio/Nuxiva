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
    r"\b(?:ciao|buongiorno|buon\s+pomeriggio|buonasera|salve|ehi|hey)\b",
    r"\b(?:come\s+va|tutto\s+bene|come\s+stai|che\s+si\s+dice)\b",
    r"\b(?:hello|hi|good\s+morning|good\s+afternoon|good\s+evening|how\s+are\s+you)\b",
    r"\b(?:hola|buenos\s+dias|buenas\s+tardes|buenas\s+noches|que\s+tal)\b",
    r"\b(?:bonjour|bon\s+apres-midi|bonsoir|salut|comment\s+ca\s+va)\b",
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

DOMAIN_PATTERNS = {
    "domain_arch": re.compile(r"\b(?:architett\w*|struttur\w*|design\w*|infrastruttur\w*|topology)\b", re.IGNORECASE),
    "domain_code": re.compile(r"\b(?:codic\w*|code|rust|python|debug\w*|test\w*|funzion\w*|algoritm\w*|bug\w*|refactor\w*)\b", re.IGNORECASE),
    "domain_system": re.compile(r"\b(?:sistem\w*|memori\w*|load\w*|cpu|telemetri\w*|server\w*|socket\w*)\b", re.IGNORECASE),
}


def _matches(patterns: tuple[str, ...], text: str) -> bool:
    for pat in patterns:
        if re.search(pat, text, re.IGNORECASE):
            return True
    return False


def _compute_salutation_key(hour: int) -> str:
    if 5 <= hour < 12:
        return "temporal_morning"
    if 12 <= hour < 18:
        return "temporal_afternoon"
    if 18 <= hour < 22:
        return "temporal_evening"
    return "temporal_general"


class AcousticReflexEngine:
    def __init__(self, memory_store=None) -> None:
        self.memory = memory_store or reflex_memory

    def evaluate(self, query: str, user_name: str | None = None, lang: str = "it") -> ReflexResponse:
        start_time = time.monotonic()
        clean_q = query.strip()
        profile = self.memory.learn(clean_q, user_name)

        is_greeting = _matches(GREETING_PATTERNS, clean_q)
        is_status = _matches(STATUS_PATTERNS, clean_q)
        is_reasoning = _matches(REASONING_PATTERNS, clean_q)

        if is_greeting and not is_reasoning:
            kind = "greeting"
            needs_deep = False
            reflex_text = self._synthesize_greeting(profile, lang)
        elif is_status and not is_reasoning:
            kind = "quick_status"
            needs_deep = False
            reflex_text = self._synthesize_status(profile, lang)
        else:
            kind = "thinking_filler"
            needs_deep = True
            reflex_text = self._synthesize_filler(clean_q, profile, lang)

        self.memory.record_usage(reflex_text, kind)
        latency_ms = round((time.monotonic() - start_time) * 1000.0, 2)

        return ReflexResponse(
            reflex_text=reflex_text,
            latency_ms=latency_ms,
            kind=kind,
            needs_deep_reasoning=needs_deep,
            persona_applied=profile.style,
        )

    def _synthesize_greeting(self, profile: PersonaProfile, lang: str) -> str:
        hour = time.localtime().tm_hour
        salutation = word(lang, "reflex", _compute_salutation_key(hour))
        address = f" {profile.user_name}!" if profile.user_name and profile.user_name != "user" else "!"

        if profile.interests:
            entity = profile.interests[-1]
            bridge = word(lang, "reflex", "bridge_interest").format(entity=entity)
        elif "technology" in profile.facts:
            entity = profile.facts["technology"]
            bridge = word(lang, "reflex", "bridge_tech").format(entity=entity)
        elif "desire" in profile.facts:
            entity = profile.facts["desire"]
            bridge = word(lang, "reflex", "bridge_desire").format(entity=entity)
        elif profile.style == "executive":
            bridge = word(lang, "reflex", "status_optimal")
        else:
            bridge = word(lang, "reflex", "bridge_open")

        return f"{salutation}{address} {bridge}"

    def _synthesize_status(self, profile: PersonaProfile, lang: str) -> str:
        optimal = word(lang, "reflex", "status_optimal")
        focus_entity = profile.facts.get("technology", profile.facts.get("desire", "Nuxiva"))
        focus_part = word(lang, "reflex", "status_focus").format(focus=focus_entity)
        return f"{optimal} {focus_part}"

    def _synthesize_filler(self, query: str, profile: PersonaProfile, lang: str) -> str:
        domain_key = "domain_general"
        for key, pat in DOMAIN_PATTERNS.items():
            if pat.search(query):
                domain_key = key
                break
        domain_text = word(lang, "reflex", domain_key)

        verb_keys = ["filler_action_eval", "filler_action_synth", "filler_action_cross", "filler_action_proc"]
        conn_keys = ["connector_now", "connector_struct", "connector_stream", "connector_instant"]

        candidates = [
            f"{word(lang, 'reflex', vk)} {domain_text} {word(lang, 'reflex', ck)}"
            for vk in verb_keys
            for ck in conn_keys
        ]
        chosen = self.memory.get_least_used(candidates) or candidates[0]
        return chosen


reflex_engine = AcousticReflexEngine()
