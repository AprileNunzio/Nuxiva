import re

from access import NO_CACHE, is_local, require_display
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse

from agenti.hands import events as hand_events
from agenti.hands import store

public_routes = APIRouter()
MAX_EVENTS = 32
MAX_FACES = 16
TYPES = frozenset({"gesture", "action"})
TOKEN = re.compile(r"^[a-z0-9_.:-]{1,48}$")
FIELDS = ("action", "gesture", "hand", "modifier")


def faces(presence: dict) -> list[dict]:
    from agenti.desktop.presence_bridge import face_signal
    out = []
    for person in (presence or {}).get("people") or []:
        if not isinstance(person, dict):
            continue
        gaze = person.get("gaze") or {}
        try:
            x, y, w = float(gaze.get("x")), float(gaze.get("y")), float(person.get("raw_proximity"))
        except (TypeError, ValueError):
            continue
        if not all(0.0 <= v <= 1.0 for v in (x, y)) or not 0.0 < w <= 1.0:
            continue
        signal = face_signal(person)
        out.append({"x": round(x, 4), "y": round(y, 4), "w": round(w, 4),
                    "authorized": bool(signal["authorized"]) and signal["liveness"] != "spoof"})
    return out[:MAX_FACES]


def semantic(event) -> dict | None:
    if not isinstance(event, dict) or event.get("type") not in TYPES:
        return None
    clean = {"type": event["type"]}
    for field in FIELDS:
        value = event.get(field)
        if value is None:
            continue
        if not isinstance(value, str) or not TOKEN.match(value):
            return None
        clean[field] = value
    if event["type"] == "action" and "action" not in clean:
        return None
    return clean


@public_routes.get("/api/hands/display/profile")
async def display_profile(request: Request):
    require_display(request, "Solo dal display")
    return JSONResponse({"revision": store.revision(), "profile": store.load()}, headers=NO_CACHE)


@public_routes.get("/api/hands/display/scene")
async def display_scene(request: Request):
    if not is_local(request):
        raise HTTPException(403, "Solo dal display del server")
    from state import store as state
    from agenti.desktop.presence_bridge import show_options
    audience = (state.audience or {}).get("kind") or "uncertain"
    return JSONResponse({"faces": faces(state.presence or {}), "audience": audience,
                         "trust_guests": show_options()["trust_guests"]}, headers=NO_CACHE)


@public_routes.post("/api/hands/display/events")
async def display_events(request: Request):
    require_display(request, "Solo dal display")
    body = await request.json()
    items = body.get("events") if isinstance(body, dict) else None
    if not isinstance(items, list) or len(items) > MAX_EVENTS:
        raise HTTPException(400, "Eventi non validi")
    clean = [semantic(e) for e in items]
    if any(e is None for e in clean):
        raise HTTPException(400, "Eventi non validi")
    hand_events.record(clean)
    return {"ok": True, "recorded": len(clean)}
