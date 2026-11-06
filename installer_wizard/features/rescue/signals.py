import math
import re

MAX_SOURCE = 96
MAX_EVIDENCE = 512
MAX_FUTURE_S = 5.0

KINDS = ("help_words", "scream", "fall", "immobility", "vitals", "no_response",
         "smoke", "fire", "intrusion", "violence", "all_clear")
HAZARDS = ("medical", "fire", "intrusion", "violence")

HAZARDS_OF = {
    "help_words": ("medical", "violence"), "scream": ("medical", "violence"), "all_clear": ("medical", "violence"),
    "fall": ("medical",), "immobility": ("medical",), "vitals": ("medical",), "no_response": ("medical",),
    "smoke": ("fire",), "fire": ("fire",), "intrusion": ("intrusion",), "violence": ("violence",),
}
MODALITY = {
    "help_words": "audio", "scream": "audio", "violence": "audio",
    "fall": "vision", "immobility": "vision", "intrusion": "vision",
    "vitals": "body", "smoke": "environment", "fire": "environment",
    "no_response": "interaction", "all_clear": "interaction",
}
RELIABILITY = {
    "help_words": 0.85, "scream": 0.6, "immobility": 0.6, "fall": 0.75, "vitals": 0.5, "no_response": 0.5,
    "smoke": 0.9, "fire": 0.9, "all_clear": 0.9, "intrusion": 0.7, "violence": 0.4,
}
HALF_LIFE = {
    "help_words": 120.0, "immobility": 120.0, "vitals": 120.0, "violence": 120.0, "scream": 60.0,
    "fall": 600.0, "no_response": 300.0, "smoke": 300.0, "fire": 300.0, "intrusion": 300.0, "all_clear": 180.0,
}
LABEL = re.compile(r"^[A-Za-z0-9_.:/-]{1,96}$")


class EvidenceError(ValueError):
    pass


def _finite(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def evidence(kind: str, probability: float, confidence: float, source: str, at: float, room: str | None = None) -> dict:
    if kind not in HAZARDS_OF:
        raise EvidenceError("rescue.evidence.kind")
    return {"kind": kind, "probability": probability, "confidence": confidence, "source": source, "room": room, "at": at}


def validate(e: dict, now: float) -> None:
    p, c, at = e.get("probability"), e.get("confidence"), e.get("at")
    if not _finite(p) or not 0.0 <= p <= 1.0:
        raise EvidenceError("rescue.evidence.probability")
    if not _finite(c) or not 0.0 <= c <= 1.0:
        raise EvidenceError("rescue.evidence.confidence")
    if not isinstance(e.get("source"), str) or not LABEL.match(e["source"]):
        raise EvidenceError("rescue.evidence.source")
    room = e.get("room")
    if room is not None and (not isinstance(room, str) or not LABEL.match(room)):
        raise EvidenceError("rescue.evidence.room")
    if not _finite(at) or at < 0.0 or not _finite(now) or at > now + MAX_FUTURE_S:
        raise EvidenceError("rescue.evidence.time")


def expired(e: dict, now: float) -> bool:
    return now - e["at"] > HALF_LIFE[e["kind"]] * 4.0
