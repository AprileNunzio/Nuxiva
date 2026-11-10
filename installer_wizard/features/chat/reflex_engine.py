from dataclasses import asdict, dataclass
import re
import time

from features.chat.reflex_memory import PersonaProfile, reflex_memory


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
)

STATUS_PATTERNS = (
    r"\b(?:situazione|stato|come\s+siamo\s+messi|riassunto|panoramica)\b",
    r"\b(?:status|overview|summary)\b",
)

REASONING_PATTERNS = (
    r"\b(?:perché|come\s+(?:fare|funziona|possiamo|risolvere|implementare)|progetta|sviluppa|analizza|risolvi|architettura|codice)\b",
    r"\b(?:why|how\s+(?:to|does|can|should)|design|develop|analyze|solve|refactor)\b",
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

        kind = "thinking_filler"
        needs_deep = True
        candidates = []

        is_greeting = _matches(GREETING_PATTERNS, clean_q)
        is_status = _matches(STATUS_PATTERNS, clean_q)
        is_reasoning = _matches(REASONING_PATTERNS, clean_q)

        if is_greeting and not is_reasoning:
            kind = "greeting"
            needs_deep = False
            candidates = self._build_greetings(profile, lang)
        elif is_status and not is_reasoning:
            kind = "quick_status"
            needs_deep = False
            candidates = self._build_status(profile, lang)
        else:
            kind = "thinking_filler"
            needs_deep = True
            candidates = self._build_fillers(profile, lang)

        chosen = self.memory.get_least_used(candidates) or candidates[0]
        self.memory.record_usage(chosen, kind)
        latency_ms = round((time.monotonic() - start_time) * 1000.0, 2)

        return ReflexResponse(
            reflex_text=chosen,
            latency_ms=latency_ms,
            kind=kind,
            needs_deep_reasoning=needs_deep,
            persona_applied=profile.style,
        )

    def _build_greetings(self, profile: PersonaProfile, lang: str) -> list[str]:
        name = profile.user_name
        is_napoli = "napoli_calcio" in profile.interests
        napoli_fact = profile.facts.get("napoli_status", "Il Napoli ha giocato una bella partita.")

        if lang == "en":
            if profile.style == "executive":
                return [
                    f"Good day {name}. All systems operational and agency departments ready. How shall we proceed?",
                    f"Welcome back {name}. Cluster telemetry is stable. What is our core priority today?",
                ]
            return [
                f"Hello {name}! Everything is running smoothly. Ready to tackle our objectives today!",
                f"Hey {name}! Great to see you. How can I assist you right now?",
            ]

        if profile.style == "executive":
            return [
                f"Buongiorno {name}. Tutti i nodi sono operativi e la pipeline è stabile. Quali sono le direttive?",
                f"Ben ritrovato {name}. Ecosistema NunzioTech Agency a regime. Da dove iniziamo?",
            ]

        if is_napoli:
            return [
                f"Tutto alla grande {name}! {napoli_fact} Che ne pensa della prestazione? Di cosa ci occupiamo oggi?",
                f"Buongiorno {name}! Con il Napoli in forma così la giornata parte alla perfezione! Qual è il piano?",
                f"Ciao {name}! Ecosistema al cento per cento e morale altissimo per il Napoli. A cosa lavoriamo?",
            ]

        return [
            f"Ciao {name}! Tutto procede a gonfie vele. Cosa vogliamo realizzare oggi?",
            f"Buongiorno {name}! Sono pronto a supportarla su qualsiasi fronte. Come posso aiutarla?",
        ]

    def _build_status(self, profile: PersonaProfile, lang: str) -> list[str]:
        name = profile.user_name
        focus = profile.facts.get("focus_today", "Sviluppo dell'architettura autonoma.")
        if lang == "en":
            return [
                f"All systems optimal, {name}. Focus: {focus}",
                f"Telemetry green across all workstations, {name}. No critical bottlenecks detected.",
            ]
        return [
            f"Siamo messi benissimo, {name}. Focus attuale: {focus}",
            f"Telemetria verde su tutte le workstation di NunzioTech Agency, {name}. Nessun collo di bottiglia rilevato.",
        ]

    def _build_fillers(self, profile: PersonaProfile, lang: str) -> list[str]:
        name = profile.user_name
        if lang == "en":
            return [
                f"Understood {name}, analyzing the system graph while synthesizing the solution...",
                f"On it {name}. Let me cross-reference the components while I formulate the best approach...",
                f"Great question {name}. Processing the reasoning chain right now...",
            ]
        return [
            f"Un attimo {name}, sto elaborando la risposta e incrociando i dati...",
            f"Subito {name}. Fammi analizzare a fondo la richiesta mentre strutturo i dettagli...",
            f"Ottimo quesito {name}, sto aggregando il contesto cognitivo proprio in questo istante...",
            f"Ricevuto {name}, verifico i parametri di sistema mentre ti preparo la soluzione completa...",
        ]


reflex_engine = AcousticReflexEngine()
