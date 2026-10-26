import time
import uuid

from features.people import people

MOODS = ("felice", "sereno", "entusiasta", "innamorato", "grato", "neutro", "stanco", "annoiato", "stressato",
         "preoccupato", "triste", "arrabbiato", "malato")
SOURCES = ("manuale", "assistente", "persona", "camera")
MAX_ENTRIES = 730
MAX_NOTE = 300
MAX_EVIDENCE = 160
VERDICTS = ("ok", "wrong")


def _clean(mood: str, intensity, note: str, source: str, evidence: str = "", at: float | None = None) -> dict:
    mood = str(mood or "").strip().lower()
    if mood not in MOODS:
        raise ValueError("stato d'animo non valido")
    try:
        level = int(intensity)
    except (TypeError, ValueError):
        raise ValueError("intensità non valida")
    if not 1 <= level <= 5:
        raise ValueError("intensità non valida")
    if source not in SOURCES:
        raise ValueError("origine non valida")
    entry = {"id": uuid.uuid4().hex[:10], "at": at or time.time(), "mood": mood, "intensity": level,
             "note": " ".join(str(note or "").split())[:MAX_NOTE], "source": source}
    if evidence:
        entry["evidence"] = " ".join(str(evidence).split())[:MAX_EVIDENCE]
        entry["feedback"] = ""
    return entry


def record(slug: str, mood: str, intensity=3, note: str = "", source: str = "manuale", evidence: str = "", at: float | None = None) -> dict:
    entry = _clean(mood, intensity, note, source, evidence, at)
    with people._lock:
        profile = people.load(slug)
        if profile is None:
            raise KeyError(slug)
        journal = list(profile.get("mood_journal") or [])
        journal.append(entry)
        profile["mood_journal"] = journal[-MAX_ENTRIES:]
        people.save(profile)
    return entry


def feedback(slug: str, entry_id: str, verdict: str, mood: str = "", intensity=None) -> dict | None:
    if verdict not in VERDICTS:
        raise ValueError("giudizio non valido")
    with people._lock:
        profile = people.load(slug)
        if profile is None:
            raise KeyError(slug)
        journal = list(profile.get("mood_journal") or [])
        target = next((e for e in journal if e.get("id") == entry_id), None)
        if target is None:
            return None
        if verdict == "ok":
            target["feedback"] = "ok"
        elif mood:
            fixed = _clean(mood, intensity if intensity is not None else target.get("intensity", 3), target.get("note", ""), "persona")
            target.update(mood=fixed["mood"], intensity=fixed["intensity"], source="persona", feedback="corrected")
        else:
            journal = [e for e in journal if e.get("id") != entry_id]
            profile["mood_rejected"] = int(profile.get("mood_rejected", 0)) + 1
        profile["mood_journal"] = journal
        people.save(profile)
    return target if verdict == "ok" or mood else {"id": entry_id, "removed": True}


def remove(slug: str, entry_id: str) -> bool:
    with people._lock:
        profile = people.load(slug)
        if profile is None:
            raise KeyError(slug)
        journal = list(profile.get("mood_journal") or [])
        kept = [e for e in journal if e.get("id") != entry_id]
        if len(kept) == len(journal):
            return False
        profile["mood_journal"] = kept
        people.save(profile)
    return True


def journal(slug: str, limit: int = 120) -> list[dict]:
    profile = people.load(slug)
    if profile is None:
        raise KeyError(slug)
    rows = [e for e in profile.get("mood_journal") or [] if isinstance(e, dict) and e.get("mood") in MOODS]
    return sorted(rows, key=lambda e: -float(e.get("at", 0)))[:limit]


def latest(slug: str) -> dict | None:
    rows = journal(slug, 1)
    return rows[0] if rows else None
