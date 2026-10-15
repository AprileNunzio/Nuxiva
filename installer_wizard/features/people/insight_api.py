from fastapi import APIRouter, Depends, HTTPException, Request

from access import require_admin
from features.people import mood, people
from state import store

admin_routes = APIRouter()
MAX_FACT = 200


def _profile(slug: str) -> dict:
    profile = people.load(slug)
    if not profile:
        raise HTTPException(404, "Persona non trovata")
    return profile


async def _body(request: Request) -> dict:
    try:
        body = await request.json()
    except ValueError:
        raise HTTPException(400, "Richiesta non valida")
    if not isinstance(body, dict):
        raise HTTPException(400, "Richiesta non valida")
    return body


def _mind():
    from features.mind.mind import mind
    return mind


@admin_routes.get("/api/people/{slug}/memories")
async def person_memories(slug: str, _: str = Depends(require_admin)):
    profile = _profile(slug)
    facts = [f for f in _mind().memory.listing() if f.get("who") == profile["slug"]]
    return {"memories": facts[:300]}


@admin_routes.post("/api/people/{slug}/memories")
async def person_memory_add(slug: str, request: Request, user: str = Depends(require_admin)):
    profile = _profile(slug)
    text = str((await _body(request)).get("text") or "").strip()
    if not 3 <= len(text) <= MAX_FACT:
        raise HTTPException(400, "Ricordo non valido")
    saved = _mind().memory.add(text, kind="persona", score=0.8, who=profile["slug"])
    _mind().publish()
    store.event("INFO", f"Ricordo aggiunto a {profile['name']} da {user}", "people")
    return saved


@admin_routes.get("/api/people/{slug}/mood")
async def person_mood(slug: str, _: str = Depends(require_admin)):
    _profile(slug)
    return {"moods": list(mood.MOODS), "journal": mood.journal(slug)}


@admin_routes.post("/api/people/{slug}/mood")
async def person_mood_add(slug: str, request: Request, user: str = Depends(require_admin)):
    _profile(slug)
    body = await _body(request)
    try:
        entry = mood.record(slug, body.get("mood"), body.get("intensity", 3), body.get("note", ""), "manuale")
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    store.event("INFO", f"Stato d'animo annotato per {slug} da {user}", "people")
    return entry


@admin_routes.delete("/api/people/{slug}/mood/{entry_id}")
async def person_mood_delete(slug: str, entry_id: str, _: str = Depends(require_admin)):
    _profile(slug)
    if not mood.remove(slug, entry_id):
        raise HTTPException(404, "Annotazione non trovata")
    return {"ok": True}
