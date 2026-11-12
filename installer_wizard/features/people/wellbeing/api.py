import json

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import PlainTextResponse

from access import require_admin
from features.people import people
from features.people.wellbeing import report, service, store
from state import store as events

admin_routes = APIRouter()
BODY = 4096


async def _json(request: Request, size: int = BODY) -> dict:
    raw = await request.body()
    if len(raw) > size:
        raise HTTPException(413, "Richiesta troppo grande")
    try:
        body = json.loads(raw) if raw else {}
    except (UnicodeDecodeError, ValueError):
        raise HTTPException(400, "Richiesta non valida")
    if not isinstance(body, dict):
        raise HTTPException(400, "Richiesta non valida")
    return body


def _person(slug: str) -> dict:
    profile = people.load(slug)
    if not profile:
        raise HTTPException(404, "Persona non trovata")
    return profile


@admin_routes.get("/api/people/{slug}/wellbeing")
async def wellbeing_state(slug: str, _: str = Depends(require_admin)):
    _person(slug)
    return service.state(slug)


@admin_routes.put("/api/people/{slug}/wellbeing/consent")
async def wellbeing_consent(slug: str, request: Request, user: str = Depends(require_admin)):
    _person(slug)
    body = await _json(request)
    if not isinstance(body.get("active"), bool):
        raise HTTPException(400, "Richiesta non valida")
    store.set_consent(slug, body["active"])
    events.event("INFO", f"Percorso di benessere {'attivato' if body['active'] else 'sospeso'} per {slug} da {user}", "wellbeing")
    return {"consent": body["active"]}


@admin_routes.post("/api/people/{slug}/wellbeing/sessions")
async def wellbeing_start(slug: str, request: Request, _: str = Depends(require_admin)):
    _person(slug)
    body = await _json(request)
    try:
        return await service.start(slug, str(body.get("lang", "it")), body.get("mood_before"))
    except PermissionError as exc:
        raise HTTPException(403, str(exc))


@admin_routes.post("/api/people/{slug}/wellbeing/sessions/{sid}/turn")
async def wellbeing_turn(slug: str, sid: str, request: Request, _: str = Depends(require_admin)):
    _person(slug)
    body = await _json(request)
    try:
        return await service.turn(slug, sid, body.get("text", ""))
    except LookupError as exc:
        raise HTTPException(404, str(exc))
    except ValueError as exc:
        raise HTTPException(400, str(exc))


@admin_routes.post("/api/people/{slug}/wellbeing/sessions/{sid}/close")
async def wellbeing_close(slug: str, sid: str, request: Request, _: str = Depends(require_admin)):
    _person(slug)
    body = await _json(request)
    try:
        return await service.close(slug, sid, body.get("mood_after"))
    except LookupError as exc:
        raise HTTPException(404, str(exc))


@admin_routes.get("/api/people/{slug}/wellbeing/report")
async def wellbeing_report(slug: str, lang: str = "it", format: str = "json", transcripts: bool = False, _: str = Depends(require_admin)):
    _person(slug)
    data = report.build(slug, lang[:2], transcripts)
    if format == "md":
        return PlainTextResponse(report.markdown(data), media_type="text/markdown; charset=utf-8")
    return data


@admin_routes.delete("/api/people/{slug}/wellbeing")
async def wellbeing_forget(slug: str, user: str = Depends(require_admin)):
    _person(slug)
    service.forget(slug)
    events.event("INFO", f"Dati di benessere eliminati per {slug} da {user}", "wellbeing")
    return {"erased": True}
