import time
from datetime import datetime, timedelta

from fastapi import APIRouter, HTTPException, Request

from access import require_display
from features.people import learning, mood, people
from state import store

public_routes = APIRouter()

HOME_WINDOW = 600
MAX_ROSTER = 8
MAX_LEARNED = 4
SERIES_DAYS = 7
MAX_BODY = 512


def initials(name: str) -> str:
    parts = [w for w in str(name or "").split() if w]
    return "".join(w[0] for w in parts[:2]).upper() or "?"


def roster(now: float, visible: set) -> list[dict]:
    rows = []
    for profile in people.all_profiles(light=True):
        stats = profile.get("stats") or {}
        seen = float(stats.get("last_seen") or 0)
        home = profile["slug"] in visible or (seen and now - seen <= HOME_WINDOW)
        rows.append({"slug": profile["slug"], "name": people.display_name(profile), "initials": initials(people.display_name(profile)),
                     "home": bool(home), "seen": seen or None, "visible": profile["slug"] in visible})
    rows.sort(key=lambda r: (not r["home"], -(r["seen"] or 0)))
    return rows[:MAX_ROSTER]


def series(slug: str, now: float) -> list[dict]:
    start = datetime.fromtimestamp(now).replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=SERIES_DAYS - 1)
    buckets = {i: [] for i in range(SERIES_DAYS)}
    for entry in mood.journal(slug, 400):
        day = (datetime.fromtimestamp(float(entry["at"])) - start).days
        if day in buckets and entry.get("feedback") != "wrong":
            buckets[day].append(entry)
    out = []
    for day in range(SERIES_DAYS):
        rows = buckets[day]
        out.append({"day": (start + timedelta(days=day)).strftime("%a"), "n": len(rows),
                    "level": round(sum(r["intensity"] for r in rows) / len(rows), 2) if rows else None,
                    "mood": max(rows, key=lambda r: r["at"])["mood"] if rows else None})
    return out


def learned_today(slug: str, now: float) -> list[dict]:
    midnight = datetime.fromtimestamp(now).replace(hour=0, minute=0, second=0, microsecond=0).timestamp()
    rows = [r for r in learning.listing(slug) if float(r.get("at", 0)) >= midnight and r.get("status") != "rejected"]
    return [{"id": r["id"], "field": r["field"], "value": r["value"], "status": r["status"]} for r in rows[:MAX_LEARNED]]


def focus_of(requested: str, visible: list) -> str:
    known = [p for p in visible if p.get("known") and p.get("slug")]
    if requested and people.load(requested) and (not known or any(p["slug"] == requested for p in known)):
        return requested
    near = next((p for p in known if p.get("near")), None)
    return (near or known[0])["slug"] if known else ""


def visible_people() -> list:
    presence = store.presence if isinstance(store.presence, dict) else {}
    return list(presence.get("people") or []) if presence.get("status") == "ok" else []


def focus_block(slug: str, now: float) -> dict | None:
    profile = people.load(slug) if slug else None
    if not profile:
        return None
    latest = mood.latest(slug)
    entry = None
    if latest and latest.get("feedback") != "wrong":
        entry = {"id": latest["id"], "mood": latest["mood"], "intensity": latest["intensity"], "evidence": latest.get("evidence", ""),
                 "source": latest["source"], "feedback": latest.get("feedback", ""), "at": latest["at"]}
    return {"slug": slug, "name": people.display_name(profile), "initials": initials(people.display_name(profile)),
            "mood": entry, "series": series(slug, now), "learned": learned_today(slug, now), "learning": learning.enabled()}


@public_routes.get("/api/display/people-panel")
async def people_panel(request: Request, focus: str = ""):
    require_display(request)
    now = time.time()
    visible = visible_people()
    slug = focus_of(focus[:64], visible)
    return {"roster": roster(now, {p["slug"] for p in visible if p.get("known") and p.get("slug")}),
            "focus": focus_block(slug, now), "at": now}


@public_routes.post("/api/display/people-panel/feedback")
async def people_panel_feedback(request: Request):
    require_display(request)
    if request.headers.get("X-Nuxiva-Request") != "1":
        raise HTTPException(403, "Richiesta non valida")
    raw = await request.body()
    if len(raw) > MAX_BODY:
        raise HTTPException(413, "Richiesta troppo grande")
    try:
        body = await request.json()
    except ValueError:
        raise HTTPException(400, "Richiesta non valida")
    if not isinstance(body, dict):
        raise HTTPException(400, "Richiesta non valida")
    kind, slug, entry_id, verdict = (str(body.get(k, ""))[:64] for k in ("kind", "slug", "id", "verdict"))
    if not people.load(slug):
        raise HTTPException(404, "Persona non trovata")
    try:
        if kind == "mood":
            result = mood.feedback(slug, entry_id, verdict)
        elif kind == "learned":
            result = learning.feedback(slug, entry_id, verdict)
        else:
            raise HTTPException(400, "Richiesta non valida")
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    if result is None:
        raise HTTPException(404, "Voce non trovata")
    store.event("INFO", f"Giudizio dal display su {kind} di {slug}: {verdict}", "people")
    return {"ok": True}
