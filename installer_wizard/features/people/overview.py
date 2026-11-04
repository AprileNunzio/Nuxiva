import time
from pathlib import Path

from features.chat import voice_id
from features.people import connectors, faces, people
from features.people.vitals import service as vitals
from features.people.vitals.history import history

LEARNED_STATES = ("auto", "confirmed")


def _filled(value) -> bool:
    if isinstance(value, (list, dict)):
        return bool(value)
    return value not in (None, "", 0, False)


def _health(slug: str, now: float) -> dict:
    values = vitals.current(slug, now)
    heart = values.get("heart_rate")
    view = vitals.health_view(slug, now)
    recovery = view.get("recovery")
    return {"metrics": len(values), "heart_rate": heart["value"] if heart else None,
            "recovery": recovery["score"] if recovery else None, "band": recovery["band"] if recovery else None,
            "signals": len(view.get("signals") or []), "history": history.span(slug)}


def _mood(profile: dict) -> dict:
    journal = [e for e in profile.get("mood_journal") or [] if isinstance(e, dict)]
    last = max(journal, key=lambda e: float(e.get("at", 0)), default=None)
    archived = sum(sum(b.values()) for b in (profile.get("mood_archive") or {}).values() if isinstance(b, dict))
    return {"entries": len(journal) + archived, "last": {k: last.get(k) for k in ("mood", "intensity", "at", "source")} if last else None}


def _memories(slug: str) -> dict:
    from features.mind.mind import mind
    facts = mind.memory.listing(who=slug)
    return {"count": len(facts), "last": facts[0]["text"] if facts else "", "at": facts[0]["updated"] if facts else None}


def _learned(profile: dict) -> dict:
    rows = [e for e in profile.get("learned") or [] if isinstance(e, dict) and e.get("status") in LEARNED_STATES]
    return {"count": len(rows), "last": rows[0] if rows else None}


def build(slug: str, sections: list[dict], faces_dir: Path, now: float | None = None) -> dict:
    now = now or time.time()
    profile = people.get(slug)
    if not profile:
        raise KeyError(slug)
    fill = {}
    for section in sections:
        keys = [f["key"] for f in section.get("fields") or []]
        fill[section["id"]] = {"filled": sum(1 for k in keys if _filled(profile.get(k))), "total": len(keys)}
    linked = [c["id"] for c in connectors.listing(slug) if c.get("linked")]
    stats = profile.get("stats") or {}
    return {
        "slug": slug, "first_name": profile.get("first_name") or "", "last_name": profile.get("last_name") or "",
        "since": profile.get("created_at"), "sections": fill,
        "face": {"quality": faces.quality(faces_dir, slug)}, "voice": voice_id.status(slug),
        "health": _health(slug, now), "mood": _mood(profile), "memories": _memories(slug), "learned": _learned(profile),
        "habits": {"summary": (profile.get("habits") or {}).get("summary", ""), "visits": stats.get("visits", 0),
                   "last_seen": stats.get("last_seen")},
        "connectors": {"linked": linked},
    }
