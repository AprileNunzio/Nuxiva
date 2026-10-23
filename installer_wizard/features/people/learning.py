import logging
import re
import time
import uuid

from config import env_get
from features.people import mood as mood_journal
from features.people import people
from state import store

log = logging.getLogger("nuxiva.people.learning")
MAX_LEARNED = 200
MAX_TAGS = 40
DEDUP_SECONDS = 1800

_COPULA = r"(?:sono|mi sento|mi sembra di essere|sto)\s+(?:(?:davvero|molto|troppo|super|veramente|proprio|assolutamente|un po'?|abbastanza|piuttosto|leggermente|così)\s+)*"
_MOOD_STEMS = {
    "stanco": r"stanc[oa]|esaust[oa]|distrutt[oa]|sfinit[oa]|a pezzi",
    "stressato": r"stressat[oa]|sotto pressione|agitat[oa]|nervos[oa]|teso|tesa",
    "preoccupato": r"preoccupat[oa]|in ansia|ansios[oa]",
    "triste": r"triste|gi[uù] di morale|abbattut[oa]|depress[oa]|malinconic[oa]",
    "arrabbiato": r"arrabbiat[oa]|furios[oa]|infuriat[oa]|incazzat[oa]|seccat[oa]",
    "annoiato": r"annoiat[oa]",
    "felice": r"felice|content[oa]|di buon umore",
    "sereno": r"seren[oa]|tranquill[oa]|rilassat[oa]",
    "entusiasta": r"entusiasta|gasat[oa]|eccitat[oa]|carico|carica",
    "innamorato": r"innamorat[oa]",
    "grato": r"grat[oa]|riconoscente",
}
_MOOD_RX = {m: re.compile(r"\b" + _COPULA + r"(?P<w>" + stems + r")\b", re.I) for m, stems in _MOOD_STEMS.items()}
_SICK_RX = re.compile(r"\b(?:ho|mi sento)\s+(?:la\s+|l['’])?(?:febbre|mal di testa|mal di gola|mal di pancia|influenza|raffreddore)\b|\bmi sento\s+(?:poco bene|male)\b", re.I)
_NEGATION = re.compile(r"\bnon\s+(?:\w+\s+){0,2}$", re.I)
_HIGH = re.compile(r"\b(?:davvero|molto|troppo|super|veramente|proprio|assolutamente|tantissimo|esaust|distrutt|sfinit|furios|infuriat|a pezzi)", re.I)
_LOW = re.compile(r"\b(?:un po'?|abbastanza|piuttosto|leggermente)\s", re.I)

_VALUE = r"([A-Za-zÀ-ÿ0-9'’&.\- ]{2,40}?)"
_END = r"(?=[.,;!?]|$|\s+(?:e|ed|ma|perché|perche)\s)"
_ART = r"(?:(?:il|lo|la|l['’]|i|gli|le|un|una)\s+)?"
PROFILE_RULES = (
    ("nickname", "text", re.compile(r"\bchiamami\s+([A-Za-zÀ-ÿ'’\-]{2,24})(?=[\s.,;!?]|$)", re.I)),
    ("coffee", "text", re.compile(r"\bil caff[eè]\s+(?:lo\s+)?(?:prendo|bevo|voglio|preferisco)\s+" + _VALUE + _END, re.I)),
    ("wake_time", "time", re.compile(r"\bmi sveglio\s+(?:di solito\s+)?alle\s+(\d{1,2})(?:[:.](\d{2}))?\b", re.I)),
    ("sleep_time", "time", re.compile(r"\bvado a (?:dormire|letto)\s+(?:di solito\s+)?alle\s+(\d{1,2})(?:[:.](\d{2}))?\b", re.I)),
    ("food_dislikes", "tags", re.compile(r"\bnon mi piace\s+mangiare\s+" + _ART + _VALUE + _END, re.I)),
    ("food_likes", "tags", re.compile(r"\b(?:mi piace|adoro|amo)\s+(?:molto\s+)?mangiare\s+" + _ART + _VALUE + _END, re.I)),
    ("music", "tags", re.compile(r"\b(?:ascolto|mi piace ascoltare|adoro ascoltare)\s+(?:la\s+)?musica\s+(?:di\s+)?" + _VALUE + _END, re.I)),
    ("music", "tags", re.compile(r"\b(?:il mio cantante|la mia band|il mio gruppo|la mia cantante)\s+(?:preferit[oa]|favorit[oa])\s+(?:è|e')\s+" + _VALUE + _END, re.I)),
    ("hobbies", "tags", re.compile(r"\b(?:il mio hobby è|la mia passione è|mi appassiona|ho la passione per)\s+" + _ART + _VALUE + _END, re.I)),
    ("sports", "tags", re.compile(r"\btifo\s+(?:per\s+)?" + _ART + _VALUE + _END, re.I)),
    ("temperature", "number", re.compile(r"\b(?:sto bene|mi trovo bene|preferisco)\s+(?:con|a)\s+(\d{2})\s*gradi\b", re.I)),
)


def enabled() -> bool:
    return env_get("NUXIVA_PEOPLE_LEARN", "1") != "0"


def detect_mood(text: str) -> tuple[str, int, str] | None:
    flat = " ".join(str(text or "").split())
    if len(flat) < 6 or flat.endswith("?"):
        return None
    for mood, rx in _MOOD_RX.items():
        m = rx.search(flat)
        if m and not _NEGATION.search(flat[:m.start()]):
            level = 4 if _HIGH.search(m.group(0)) else 2 if _LOW.search(m.group(0) + " ") else 3
            return mood, level, flat[max(0, m.start() - 20):m.end() + 40].strip()
    m = _SICK_RX.search(flat)
    if m and not _NEGATION.search(flat[:m.start()]):
        return "malato", 3, flat[max(0, m.start() - 10):m.end() + 40].strip()
    return None


def _clean_value(raw: str) -> str:
    value = " ".join(str(raw or "").replace("’", "'").split()).strip(" .,;:!?-'")
    return value[:40] if len(value) >= 2 and re.fullmatch(r"[\w'&. \-À-ÿ]+", value) else ""


def extract_profile(text: str) -> list[dict]:
    flat = " ".join(str(text or "").split())
    found, seen = [], set()
    if len(flat) < 8 or flat.endswith("?"):
        return found
    for field, kind, rx in PROFILE_RULES:
        m = rx.search(flat)
        if not m:
            continue
        if kind == "time":
            hour, minute = int(m.group(1)), int(m.group(2) or 0)
            value = f"{hour:02d}:{minute:02d}" if hour < 24 and minute < 60 else ""
        elif kind == "number":
            value = m.group(1) if 14 <= int(m.group(1)) <= 30 else ""
        else:
            value = _clean_value(m.group(1))
        if value and (field, value.lower()) not in seen:
            seen.add((field, value.lower()))
            found.append({"field": field, "kind": kind, "value": value, "evidence": flat[max(0, m.start() - 10):m.end() + 20].strip()[:160]})
    return found


def _rejected(profile: dict, field: str, value: str) -> bool:
    return any(e.get("status") == "rejected" and e.get("field") == field and str(e.get("value")).lower() == value.lower()
               for e in profile.get("learned") or [])


def _apply(profile: dict, item: dict) -> bool:
    field, kind, value = item["field"], item["kind"], item["value"]
    current = profile.get(field)
    if kind == "tags":
        items = [str(x) for x in current or []] if isinstance(current, list) else []
        if value.lower() in (x.lower() for x in items) or len(items) >= MAX_TAGS:
            return False
        profile[field] = items + [value]
        return True
    if current not in (None, "", 0):
        return False
    profile[field] = int(value) if kind == "number" else value
    return True


def _log(profile: dict, item: dict) -> dict:
    row = {"id": uuid.uuid4().hex[:10], "at": time.time(), "field": item["field"], "kind": item["kind"], "value": item["value"],
           "evidence": item["evidence"], "status": "auto"}
    profile["learned"] = ([row] + list(profile.get("learned") or []))[:MAX_LEARNED]
    return row


def learn_profile(slug: str, text: str) -> list[dict]:
    items = extract_profile(text)
    if not items:
        return []
    added = []
    with people._lock:
        profile = people.load(slug)
        if profile is None or not profile.get("consent", True):
            return []
        for item in items:
            if not _rejected(profile, item["field"], item["value"]) and _apply(profile, item):
                added.append(_log(profile, item))
        if added:
            people.save(profile)
    return added


def learn_mood(slug: str, text: str) -> dict | None:
    found = detect_mood(text)
    if not found:
        return None
    mood, level, evidence = found
    profile = people.load(slug)
    if profile is None or not profile.get("consent", True):
        return None
    now = time.time()
    for entry in profile.get("mood_journal") or []:
        if entry.get("source") == "assistente" and entry.get("mood") == mood and now - float(entry.get("at", 0)) < DEDUP_SECONDS:
            return None
    return mood_journal.record(slug, mood, level, "", "assistente", evidence)


def observe(said: str, slug: str) -> dict:
    if not enabled() or not slug or not said:
        return {"mood": None, "profile": []}
    try:
        mood = learn_mood(slug, said)
        added = learn_profile(slug, said)
    except (KeyError, ValueError, OSError) as exc:
        log.warning("Apprendimento su %s non riuscito: %s", slug, exc)
        return {"mood": None, "profile": []}
    if mood or added:
        parts = ([f"stato d'animo {mood['mood']}"] if mood else []) + [f"{a['field']}: {a['value']}" for a in added]
        store.event("INFO", f"Appreso su {slug} dalla conversazione: {', '.join(parts)}", "people")
    return {"mood": mood, "profile": added}


def listing(slug: str, limit: int = 60) -> list[dict]:
    profile = people.load(slug)
    if profile is None:
        raise KeyError(slug)
    return [e for e in profile.get("learned") or [] if isinstance(e, dict)][:limit]


def feedback(slug: str, entry_id: str, verdict: str) -> dict | None:
    if verdict not in ("ok", "wrong"):
        raise ValueError("giudizio non valido")
    with people._lock:
        profile = people.load(slug)
        if profile is None:
            raise KeyError(slug)
        row = next((e for e in profile.get("learned") or [] if e.get("id") == entry_id), None)
        if row is None:
            return None
        if verdict == "ok":
            row["status"] = "confirmed"
        else:
            row["status"] = "rejected"
            current = profile.get(row["field"])
            if isinstance(current, list):
                profile[row["field"]] = [x for x in current if str(x).lower() != str(row["value"]).lower()]
            elif str(current).lower() == str(row["value"]).lower():
                profile[row["field"]] = 0 if row["kind"] == "number" else ""
        people.save(profile)
    return row


async def observe_async(said: str, slug: str) -> None:
    observe(said, slug)
