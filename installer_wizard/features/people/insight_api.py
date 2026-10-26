import json

from fastapi import APIRouter, Depends, HTTPException, Request

from access import require_admin
from features.people import learning, mood, people
from features.mind.api_errors import failure
from features.mind.persistence import MemoryStorageError
from features.mind.records import MemoryInputError
from state import store

admin_routes = APIRouter()
MAX_FACT = 200
MAX_MEMORY_REQUEST_BYTES = 4096


def _profile(slug: str) -> dict:
    profile = people.load(slug)
    if not profile:
        raise HTTPException(404, "Persona non trovata")
    return profile


async def _body(request: Request) -> dict:
    try:
        chunks = []
        size = 0
        async for chunk in request.stream():
            size += len(chunk)
            if size > MAX_MEMORY_REQUEST_BYTES:
                raise HTTPException(413, "Richiesta troppo grande")
            chunks.append(chunk)
        body = json.loads(b"".join(chunks))
    except (UnicodeDecodeError, json.JSONDecodeError):
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
    try:
        facts = _mind().memory.listing(who=profile["slug"])
    except MemoryStorageError as exc:
        raise failure(exc) from exc
    return {"memories": facts[:300]}


@admin_routes.post("/api/people/{slug}/memories")
async def person_memory_add(slug: str, request: Request, user: str = Depends(require_admin)):
    profile = _profile(slug)
    body = await _body(request)
    if set(body) - {"text", "scope", "expires_at"}:
        raise failure("invalid_memory")
    try:
        saved = _mind().memory.add(body.get("text"), kind="persona", score=0.8, who=profile["slug"], origin="manual",
                                   scope=body.get("scope", "personal"), expires_at=body.get("expires_at"))
    except (MemoryInputError, MemoryStorageError) as exc:
        raise failure(exc) from exc
    _mind().publish()
    store.event("INFO", f"Ricordo aggiunto a {profile['name']} da {user}", "people")
    return saved


@admin_routes.patch("/api/people/{slug}/memories/{fid}")
async def person_memory_correct(slug: str, fid: str, request: Request, user: str = Depends(require_admin)):
    profile = _profile(slug)
    try:
        saved = _mind().memory.update(fid, await _body(request), who=profile["slug"])
        if saved is None:
            raise failure("unknown_memory")
    except (MemoryInputError, MemoryStorageError) as exc:
        raise failure(exc) from exc
    _mind().publish()
    store.event("INFO", f"Ricordo corretto per {profile['name']} da {user}", "people")
    return saved


@admin_routes.delete("/api/people/{slug}/memories/{fid}")
async def person_memory_remove(slug: str, fid: str, _: str = Depends(require_admin)):
    profile = _profile(slug)
    try:
        if not _mind().memory.forget(fid, who=profile["slug"]):
            raise failure("unknown_memory")
    except MemoryStorageError as exc:
        raise failure(exc) from exc
    _mind().publish()
    return {"ok": True}


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


@admin_routes.post("/api/people/{slug}/mood/{entry_id}/feedback")
async def person_mood_feedback(slug: str, entry_id: str, request: Request, user: str = Depends(require_admin)):
    _profile(slug)
    body = await _body(request)
    try:
        result = mood.feedback(slug, entry_id, str(body.get("verdict", "")), str(body.get("mood") or ""), body.get("intensity"))
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    if result is None:
        raise HTTPException(404, "Annotazione non trovata")
    store.event("INFO", f"Giudizio sullo stato d'animo di {slug} da {user}: {body.get('verdict')}", "people")
    return result


@admin_routes.get("/api/people/{slug}/learned")
async def person_learned(slug: str, _: str = Depends(require_admin)):
    _profile(slug)
    return {"enabled": learning.enabled(), "learned": learning.listing(slug)}


@admin_routes.post("/api/people/{slug}/learned/{entry_id}/feedback")
async def person_learned_feedback(slug: str, entry_id: str, request: Request, user: str = Depends(require_admin)):
    _profile(slug)
    body = await _body(request)
    try:
        row = learning.feedback(slug, entry_id, str(body.get("verdict", "")))
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    if row is None:
        raise HTTPException(404, "Informazione non trovata")
    store.event("INFO", f"Giudizio su un'informazione appresa su {slug} da {user}: {body.get('verdict')}", "people")
    return row
