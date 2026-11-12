from fastapi import APIRouter, Depends, HTTPException, Request

from access import require_admin
from state import store

from features.agent import registry
from features.experts import live, service, skills, templates
from features.experts.model import ID_RE, ExpertError
from features.experts.store import experts
from features.team.board import board

public_routes = APIRouter()
admin_routes = APIRouter()


def _lang(request: Request) -> str:
    from features.locale.api import page_language
    return templates.lang_of(page_language(request, True))


async def _body(request: Request) -> dict:
    try:
        body = await request.json()
    except ValueError:
        raise HTTPException(400, "Richiesta non valida")
    if not isinstance(body, dict):
        raise HTTPException(400, "Richiesta non valida")
    return body


def _id(expert_id: str) -> str:
    if not ID_RE.fullmatch(expert_id):
        raise HTTPException(404, "Esperto sconosciuto")
    try:
        experts.get(expert_id)
    except KeyError:
        raise HTTPException(404, "Esperto sconosciuto")
    return expert_id


def _profile(expert) -> dict:
    doing = board.current().get(service.board_key(expert.id))
    return {**expert.to_dict(), "doing": doing["what"] if doing else "", "pending": service.pending(expert.id)}


async def _as_owner(task):
    from features.authz import resolve
    from features.authz.principal import act_as, current
    token = act_as(resolve.for_session())
    try:
        return await task
    finally:
        current.reset(token)


def _tools() -> list[dict]:
    return sorted(({"name": t["name"], "description": t["description"][:240], "full_only": bool(t["full_only"])}
                   for t in registry.TOOLS.values() if not t["name"].startswith(("expert_", "team_", "agent_"))),
                  key=lambda t: t["name"])


@admin_routes.get("/api/experts")
async def overview(request: Request, _: str = Depends(require_admin)):
    lang = _lang(request)
    return {"experts": [_profile(e) for e in experts.all()], "templates": templates.catalog(lang), "tools": _tools(),
            "skills": skills.catalog(lang)}


@admin_routes.post("/api/experts")
async def create(request: Request, user: str = Depends(require_admin)):
    try:
        expert = service.create(await _body(request), _lang(request), user)
    except ExpertError as exc:
        raise HTTPException(400, str(exc))
    return _profile(expert)


@admin_routes.put("/api/experts/{expert_id}")
async def update(expert_id: str, request: Request, user: str = Depends(require_admin)):
    try:
        expert = service.update(_id(expert_id), await _body(request))
    except ExpertError as exc:
        raise HTTPException(400, str(exc))
    store.event("INFO", f"Esperto {expert_id} aggiornato da {user}", "experts")
    return _profile(expert)


@admin_routes.delete("/api/experts/{expert_id}")
async def delete(expert_id: str, user: str = Depends(require_admin)):
    service.delete(_id(expert_id))
    store.event("INFO", f"Esperto {expert_id} eliminato da {user}", "experts")
    return {"ok": True}


@admin_routes.get("/api/experts/{expert_id}/history")
async def history(expert_id: str, _: str = Depends(require_admin)):
    return {"turns": experts.history(_id(expert_id)), "pending": service.pending(expert_id)}


@admin_routes.delete("/api/experts/{expert_id}/history")
async def forget(expert_id: str, _: str = Depends(require_admin)):
    experts.forget(_id(expert_id))
    return {"ok": True}


@admin_routes.post("/api/experts/{expert_id}/ask")
async def ask(expert_id: str, request: Request, _: str = Depends(require_admin)):
    question = str((await _body(request)).get("question") or "")
    try:
        return await _as_owner(service.ask(_id(expert_id), question, _lang(request)))
    except service.ExpertBusy:
        raise HTTPException(409, "L'esperto sta già lavorando")
    except ExpertError as exc:
        raise HTTPException(400, str(exc))


@admin_routes.post("/api/experts/{expert_id}/confirm")
async def confirm(expert_id: str, request: Request, _: str = Depends(require_admin)):
    yes = (await _body(request)).get("yes") is True
    try:
        return await _as_owner(service.confirm(_id(expert_id), yes))
    except LookupError:
        raise HTTPException(409, "Nessuna azione in attesa di conferma")


@admin_routes.get("/api/experts/{expert_id}/live")
async def live_panel(expert_id: str, _: str = Depends(require_admin)):
    expert = experts.get(_id(expert_id))
    try:
        return await live.snapshot(expert.live, expert.id)
    except Exception as exc:
        store.event("WARN", f"Pannello dal vivo di {expert_id} non disponibile: {exc}", "experts")
        raise HTTPException(503, "Dati dal vivo non disponibili")
