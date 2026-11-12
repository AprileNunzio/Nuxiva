import re

from fastapi import APIRouter, Depends, HTTPException, Request

from access import require_admin, require_display

public_routes = APIRouter()
admin_routes = APIRouter()
MAX_EVENTS = 32
SLUG = re.compile(r"^[a-z0-9_.-]{1,64}$")


@public_routes.post("/api/display/feedback")
async def display_feedback(request: Request):
    require_display(request, "Solo dal display")
    body = await request.json()
    events = body.get("events") if isinstance(body, dict) else None
    if not isinstance(events, list) or len(events) > MAX_EVENTS:
        raise HTTPException(400, "Segnali non validi")
    from agenti.desktop.learner_bridge import bridge
    accepted = 0
    for event in events:
        if not isinstance(event, dict):
            raise HTTPException(400, "Segnali non validi")
        key, kind = str(event.get("key") or "")[:120], str(event.get("kind") or "")[:16]
        accepted += bridge.interacted(key, kind)
    return {"ok": True, "accepted": accepted}


@admin_routes.get("/api/display/learning")
async def display_learning(person: str | None = None, _: str = Depends(require_admin)):
    if person is not None and not SLUG.match(person):
        raise HTTPException(400, "Persona non valida")
    from agenti.desktop.learner_bridge import bridge
    return bridge.metrics(person)


@admin_routes.delete("/api/display/learning/{person}")
async def display_learning_reset(person: str, _: str = Depends(require_admin)):
    if not SLUG.match(person):
        raise HTTPException(400, "Persona non valida")
    from agenti.desktop.learner_bridge import bridge
    return {"ok": True, "removed": bridge.reset(person)}
