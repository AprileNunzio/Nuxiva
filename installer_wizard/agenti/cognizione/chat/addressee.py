import re
from dataclasses import dataclass

import native_core
from config import env_get
from state import store

from agenti.chat.dialogue import dialogue
from agenti.people import identity

MAX_LAST = 32_000
VOICE_RECENT_SECONDS = 60


def _num(key: str, default: float, lo: float, hi: float) -> float:
    try:
        return max(lo, min(hi, float(env_get(key, str(default)) or default)))
    except ValueError:
        return default


def _name_parts() -> tuple[str, list[str]]:
    raw = env_get("NUXIVA_ASSISTANT_NAME", "Nuxiva").strip()
    aliases_raw = env_get("NUXIVA_WAKE_PHONETIC_ALIASES", "").strip()
    aliases = [a.strip().lower() for a in aliases_raw.split(",") if a.strip()] if aliases_raw else []
    return raw, aliases


def _active_name_pattern() -> str:
    raw, aliases = _name_parts()
    clean = re.sub(r"^(?:hey|hei|ehi|hi|ok|okay)\s+", "", raw, flags=re.I).strip()
    primary = clean.lower() or "nuxiva"
    if primary not in aliases:
        aliases.insert(0, primary)
    if primary == "nuxiva" and "attena" not in aliases:
        aliases.append("attena")
    return "|".join(re.escape(a) for a in aliases)

def get_name_re() -> re.Pattern:
    return re.compile(rf"\b(?:{_active_name_pattern()})\b", re.I)

def get_third_person_re() -> re.Pattern:
    p = _active_name_pattern()
    return re.compile(rf"\b(?:lui|lei|(?:{p}) (?:è|e'|ha|fa|sta)|il computer|questo coso)\b", re.I)

FILLER = re.compile(r"^\W*(?:mh+|m+|eh+|ah+|oh+|boh|mah|ok(?:ay)?|va be(?:ne)?|beh|allora|niente|nulla|ahah\w*)\W*$", re.I)
ANSWER = re.compile(r"^\W*(?:s[iì]|no|certo|esatto|giusto|perfetto|grazie|ok|va bene|d'accordo|fallo|procedi|annulla|"
                    r"lascia (?:stare|perdere)|non importa)\b", re.I)
REQUEST = re.compile(r"\?\s*$|^\W*(?:e\s+)?(?:come|cosa|cos'|dove|quando|quanto|quant[aei]|quale|quali|perch[eé]|"
                     r"dimmi|dammi|fammi|mostra|apri|chiudi|accendi|spegni|metti|togli|alza|abbassa|cerca|trova|"
                     r"calcola|crea|aggiungi|leggi|ricorda|ricordami|imposta|attiva|disattiva|avvia|ferma|riproduci|"
                     r"manda|invia|chiama|prenota|spiega|traduci|continua|ripeti|puoi|potresti|sai|conosci)\b", re.I)
COMMAND = re.compile(r"^\W*(?:accendi|spegni|metti|alza|abbassa|apri|chiudi|avvia|ferma|imposta|attiva|disattiva|"
                     r"riproduci|mostrami|dimmi|ricordami|aggiungi|cerca|chiama|manda|leggimi|calcola)\b", re.I)
SECOND_PERSON = re.compile(r"\b(?:tu|ti|te|tuo|tua|puoi|sai|hai|potresti|vorresti|pensi|dimmi|fammi)\b", re.I)
WORD = re.compile(r"[a-zà-ÿ]{4,}", re.I)
FIRST_WORD = re.compile(r"^\W*([A-Za-zÀ-ÿ']+)")


@dataclass
class Verdict:
    directed: bool
    score: float
    reason: str


@dataclass(frozen=True)
class Scene:
    alone: bool
    facing: bool
    asked_question: bool
    since_reply: float
    last_turn: str | None
    present_names: tuple[str, ...]
    alone_score: float
    threshold: float
    same_speaker: bool | None = None
    voices_active: int | None = None
    mixed_speakers: bool | None = None


_rules: dict[tuple, object] = {}


def _engine():
    cls = native_core.symbol("RustAddressee")
    if cls is None:
        native_core.python_fallback("chat.addressee")
        return None
    name, aliases = _name_parts()
    key = (name, tuple(aliases))
    rules = _rules.get(key)
    if rules is None:
        _rules.clear()
        rules = _rules[key] = cls(name, aliases)
    return rules


def flag(value) -> bool | None:
    return value if isinstance(value, bool) else None


def voices(value) -> int | None:
    return max(0, min(64, value)) if isinstance(value, int) and not isinstance(value, bool) else None


def scene(device: str, heard: dict | None = None) -> Scene:
    heard = heard or {}
    people = store.presence.get("people", [])
    last = dialogue.last(device)
    return Scene(
        alone=len(people) <= 1,
        facing=any(p.get("facing") for p in people),
        asked_question=dialogue.asked_question(device),
        since_reply=float(dialogue.since_reply(device)),
        last_turn=(last.text + " " + last.reply)[:MAX_LAST] if last else None,
        present_names=tuple(n for n in (identity.first_name(p).lower() for p in identity.present()) if n)[:64],
        alone_score=_num("NUXIVA_ADDRESSEE_ALONE", 0.35, 0.0, 1.0),
        threshold=_num("NUXIVA_ADDRESSEE_THRESHOLD", 0.5, 0.2, 0.95),
        same_speaker=flag(heard.get("same_speaker")),
        voices_active=voices(heard.get("voices_active")),
        mixed_speakers=flag(heard.get("mixed_speakers")),
    )


def judge(text: str, device: str, heard: dict | None = None) -> Verdict:
    return decide(text, scene(device, heard))


def decide(text: str, ctx: Scene) -> Verdict:
    rules = _engine()
    if rules is None:
        return _py_decide(text, ctx)
    directed, score, reason = rules.judge(
        text, alone=ctx.alone, facing=ctx.facing, asked_question=ctx.asked_question, since_reply=ctx.since_reply,
        last_turn=ctx.last_turn, present_names=list(ctx.present_names), alone_score=ctx.alone_score,
        threshold=ctx.threshold, same_speaker=ctx.same_speaker, voices_active=ctx.voices_active,
        mixed_speakers=ctx.mixed_speakers)
    return Verdict(directed, round(score, 2), reason)


def _overlap(previous: str | None, text: str) -> float:
    if not previous:
        return 0.0
    before = set(WORD.findall(previous.lower()))
    now = set(WORD.findall(text.lower()))
    return len(before & now) / max(1, len(now))


def _py_decide(text: str, ctx: Scene) -> Verdict:
    third_re = get_third_person_re()
    if get_name_re().search(text) and not third_re.search(text):
        return Verdict(True, 1.0, "mi ha chiamato per nome")
    score = ctx.alone_score if ctx.alone else 0.0
    reasons = []
    if FILLER.match(text):
        return Verdict(False, 0.0, "intercalare")
    if ANSWER.match(text) and ctx.asked_question:
        return Verdict(True, 0.9, "risposta alla mia domanda")
    if COMMAND.search(text):
        score += 0.45
        reasons.append("comando")
    elif REQUEST.search(text):
        score += 0.35
        reasons.append("richiesta")
    if SECOND_PERSON.search(text):
        score += 0.15
        reasons.append("rivolto a me")
    if ctx.facing:
        score += 0.2
        reasons.append("guarda lo schermo")
    if _overlap(ctx.last_turn, text) >= 0.25:
        score += 0.2
        reasons.append("stesso argomento")
    if ctx.since_reply < 12:
        score += 0.15
    first = (FIRST_WORD.match(text) or [None, ""])[1].lower()
    if first and first in ctx.present_names:
        score -= 0.6
        reasons.append("parla con un'altra persona")
    if third_re.search(text):
        score -= 0.3
        reasons.append("parla di me in terza persona")
    if not ctx.alone and not ctx.facing:
        score -= 0.1
    if ctx.same_speaker is True and ctx.since_reply < VOICE_RECENT_SECONDS:
        score += 0.15
        reasons.append("stessa persona di prima")
    if (ctx.voices_active or 0) >= 2 and not ctx.facing:
        score -= 0.1
        reasons.append("più voci nella stanza")
    if ctx.mixed_speakers is True:
        score -= 0.15
        reasons.append("più persone nella stessa frase")
    return Verdict(score >= ctx.threshold, round(score, 2), ", ".join(reasons) or "conversazione generica")
