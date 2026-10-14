import math
import re
import time
from typing import Any, Dict, Optional


def compute_emotional_salience(
    valence: float = 0.0,
    arousal: float = 0.3,
    dopamine: float = 0.5,
    noradrenaline: float = 0.2,
) -> float:
    emotional_intensity = abs(valence) * 0.55 + arousal * 0.45
    neuro_boost = 1.0 + (dopamine * 1.8) + (noradrenaline * 2.2)
    return max(1.0, min(10.0, (1.0 + (emotional_intensity * 3.0)) * neuro_boost))


def score_memory_retention(
    memory_entry: Dict[str, Any],
    query_similarity: float,
    now_ts: Optional[float] = None,
) -> float:
    now = now_ts if now_ts is not None else time.time()
    created_at = float(memory_entry.get("timestamp", memory_entry.get("created", now)))
    age_hours = max(0.0, (now - created_at) / 3600.0)
    base_importance = float(memory_entry.get("importance", memory_entry.get("score", 0.5)))
    rehearsals = int(memory_entry.get("rehearsals", memory_entry.get("hits", 1)))
    limbic_meta = memory_entry.get("limbic", {})
    salience = compute_emotional_salience(
        valence=float(limbic_meta.get("valence", 0.0)),
        arousal=float(limbic_meta.get("arousal", 0.3)),
        dopamine=float(limbic_meta.get("dopamine", 0.5)),
        noradrenaline=float(limbic_meta.get("noradrenaline", 0.2)),
    )
    half_life_hours = 24.0 * salience * (1.0 + math.log1p(rehearsals))
    retention_decay = math.exp(-age_hours / max(1.0, half_life_hours))
    return round((query_similarity * 0.55) + (base_importance * retention_decay * 0.45), 6)


QUESTION = re.compile(r"\?\s*$|\b(?:come|cosa|cos'|dove|quando|quanto|quant[aei]|quale|quali|perch[eé]|chi)\b", re.I)
COMMAND = re.compile(r"\b(?:accendi|spegni|metti|alza|abbassa|apri|chiudi|avvia|ferma|imposta|attiva|disattiva|"
                     r"riproduci|mostra|dimmi|ricorda|aggiungi|cerca|chiama|manda|calcola|crea|leggi)\b", re.I)
DURABLE = re.compile(r"\b(?:mi chiamo|il mio|la mia|i miei|le mie|ricorda|preferisc|mi piace|adoro|odio|abito|vivo|"
                     r"lavoro|sono un|sono una|il mio obiettivo|voglio imparare|sto studiando)\b", re.I)
TRANSIENT = re.compile(r"^\W*(?:ciao|grazie|ok|okay|va bene|perfetto|bene|certo|sì|si|no|boh|mah|ahah)\b", re.I)


def clamp(v: float) -> float:
    return round(max(0.0, min(1.0, v)), 2)


def evaluate(said: str, reply: str, intent: str, context_overlap: float) -> dict:
    n = len(said)
    relevance = context_overlap if context_overlap else (0.5 if intent not in ("conversation", "") else 0.3)
    importance = 0.2
    if COMMAND.search(said):
        importance += 0.3
    if QUESTION.search(said):
        importance += 0.2
    if DURABLE.search(said):
        importance += 0.35
    if intent in ("action", "home", "introduce", "voice_id"):
        importance += 0.2
    if n > 80:
        importance += 0.1
    if TRANSIENT.match(said) and n < 25:
        importance -= 0.3
    memorability = 0.0
    if DURABLE.search(said):
        memorability += 0.6
    if intent in ("introduce", "voice_id", "place"):
        memorability += 0.3
    if n < 15 or TRANSIENT.match(said):
        memorability -= 0.3
    return {"relevance": clamp(relevance), "importance": clamp(importance),
            "memorability": clamp(memorability), "overlap": clamp(context_overlap)}
