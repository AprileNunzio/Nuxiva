import json
import math

try:
    import native_core
except ImportError:
    native_core = None

try:
    from distress_rules import HYPOTHETICAL, HYPOTHETICAL_PAIRS, NEEDS, NEGATORS, NO, PHRASES, REPORTED, TASK_WORDS, YES
except ImportError:
    from agenti.ear.distress_rules import (HYPOTHETICAL, HYPOTHETICAL_PAIRS, NEEDS, NEGATORS, NO, PHRASES, REPORTED,
                                             TASK_WORDS, YES)

MAX_TEXT = 4096
MAX_WORDS = 256
NEGATION_REACH = 3
HYPOTHETICAL_FACTOR = 0.35
REPORTED_FACTOR = 0.6
TASK_FACTOR = 0.25
MEDIA_FACTOR = 0.5
SHORT_ANSWER = 4
CUES = ("help", "emergency", "medical", "threat", "fire", "not_ok", "ok")
ALARMING = {"help", "emergency", "medical", "threat", "fire"}
ACCENTS = {**dict.fromkeys("àáâäãå", "a"), **dict.fromkeys("èéêë", "e"), **dict.fromkeys("ìíîï", "i"),
           **dict.fromkeys("òóôöõ", "o"), **dict.fromkeys("ùúûü", "u"), "ç": "c", "ñ": "n"}
ORDERED = sorted(PHRASES, key=lambda p: (-len(p[0].split(" ")), CUES.index(p[1]), p[0].encode()))


def fold(text: str) -> str:
    out = []
    for c in text:
        if c in "'-":
            c = " "
        lower = c.lower()[:1] or c
        base = ACCENTS.get(lower, lower)
        if (base.isascii() and base.isalnum()) or base == " ":
            out.append(base)
    return " ".join("".join(out).split())


def words_of(text: str) -> list[str]:
    spaced = "".join(" " if c.isspace() else c for c in text[:MAX_TEXT])
    return [w for w in fold(spaced).split(" ") if w][:MAX_WORDS]


def _run(words: list[str], phrase: str) -> bool:
    parts = phrase.split(" ")
    return any(words[i:i + len(parts)] == parts for i in range(len(words) - len(parts) + 1))


def _negator_before(words: list[str], start: int) -> bool:
    return any(w in NEGATORS for w in words[max(0, start - NEGATION_REACH):start])


def _negated(words: list[str], start: int) -> bool:
    if _negator_before(words, start):
        return True
    return any(words[i] in NEEDS and _negator_before(words, i) for i in range(max(0, start - NEGATION_REACH), start))


def _context(words: list[str]) -> float:
    factor = 1.0
    if any(w in HYPOTHETICAL for w in words) or any(_run(words, p) for p in HYPOTHETICAL_PAIRS):
        factor *= HYPOTHETICAL_FACTOR
    if any(_run(words, p) for p in REPORTED):
        factor *= REPORTED_FACTOR
    return factor


def _scan(words: list[str], factor: float) -> list[dict]:
    used = [False] * len(words)
    found = []
    for phrase, cue, lang, weight in ORDERED:
        parts = phrase.split(" ")
        i = 0
        while i + len(parts) <= len(words):
            end = i + len(parts)
            if not any(used[i:end]) and words[i:end] == parts:
                for k in range(i, end):
                    used[k] = True
                p = weight * factor
                if cue == "help" and end < len(words) and words[end] in TASK_WORDS:
                    p *= TASK_FACTOR
                found.append({"cue": cue, "phrase": phrase, "lang": lang, "start": i, "probability": p,
                              "negated": cue in ALARMING and _negated(words, i)})
                i = end
            else:
                i += 1
    found.sort(key=lambda d: (d["start"], CUES.index(d["cue"])))
    return found


def _combine(found: list[dict], cues: tuple) -> float:
    rest = 1.0
    for d in found:
        if not d["negated"] and d["cue"] in cues:
            rest *= 1.0 - min(1.0, max(0.0, d["probability"]))
    return min(1.0, max(0.0, 1.0 - rest))


def _short(words: list[str]) -> str | None:
    if not words or len(words) > SHORT_ANSWER:
        return None
    joined = " ".join(words)
    if joined in NO:
        return "not_ok"
    if joined in YES or words[0] in YES:
        return "ok"
    return None


def py_analyze(text: str, asked: bool = False, media: bool = False, speech_confidence: float = 0.8) -> dict:
    words = words_of(str(text))
    found = _scan(words, _context(words))
    alarmed = any(not d["negated"] and d["cue"] in ("help", "emergency", "medical") for d in found)
    if alarmed or any(d["cue"] == "not_ok" for d in found):
        answer = "not_ok"
    elif any(d["cue"] == "ok" for d in found):
        answer = "ok"
    else:
        answer = _short(words) if asked else None
    base = min(1.0, max(0.0, speech_confidence)) if isinstance(speech_confidence, (int, float)) and math.isfinite(speech_confidence) else 0.0
    lang = next((d["lang"] for d in found if not d["negated"]), None)
    return {"detections": found, "help": _combine(found, ("help", "emergency", "medical")),
            "threat": _combine(found, ("threat",)), "fire": _combine(found, ("fire",)),
            "confidence": base * MEDIA_FACTOR if media else base, "answer": answer, "lang": lang}


def analyze(text: str, asked: bool = False, media: bool = False, speech_confidence: float = 0.8,
            prefer_native: bool = True) -> dict:
    fn = native_core.symbol("ear_distress") if prefer_native and native_core is not None else None
    if fn is not None:
        return json.loads(fn(str(text)[:MAX_TEXT * 4], bool(asked), bool(media), float(speech_confidence)))
    if prefer_native and native_core is not None:
        native_core.python_fallback("ear.distress")
    return py_analyze(text, asked, media, speech_confidence)
