from fastapi import APIRouter, Depends, HTTPException, Request

from access import require_admin, require_display
from state import store

from features.projects import service
from features.projects.model import ID_RE, ProjectError
from features.projects.store import projects

public_routes = APIRouter()
admin_routes = APIRouter()
DISPLAY_ACTIONS = {"pause": service.pause, "resume": service.resume, "retry": service.retry, "cancel": service.cancel}


def _lang(request: Request) -> str:
    from features.experts import templates
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


def _id(project_id: str) -> str:
    if not ID_RE.fullmatch(project_id):
        raise HTTPException(404, "Progetto sconosciuto")
    try:
        projects.get(project_id)
    except KeyError:
        raise HTTPException(404, "Progetto sconosciuto")
    return project_id


def _act(action, project_id: str):
    try:
        return action(_id(project_id)).to_dict()
    except ProjectError as exc:
        raise HTTPException(400, str(exc))


@admin_routes.get("/api/projects")
async def overview(_: str = Depends(require_admin)):
    return {"projects": [p.to_dict() for p in reversed(projects.all())]}


@admin_routes.post("/api/projects")
async def create(request: Request, user: str = Depends(require_admin)):
    body = await _body(request)
    try:
        project = service.start(str(body.get("goal") or ""), _lang(request), str(body.get("title") or ""))
    except ProjectError as exc:
        raise HTTPException(400, str(exc))
    store.event("INFO", f"Progetto {project.id} creato da {user}", "projects")
    return project.to_dict()


@admin_routes.post("/api/projects/{project_id}/pause")
async def pause(project_id: str, _: str = Depends(require_admin)):
    return _act(service.pause, project_id)


@admin_routes.post("/api/projects/{project_id}/resume")
async def resume(project_id: str, _: str = Depends(require_admin)):
    return _act(service.resume, project_id)


@admin_routes.post("/api/projects/{project_id}/retry")
async def retry(project_id: str, _: str = Depends(require_admin)):
    return _act(service.retry, project_id)


@admin_routes.post("/api/projects/{project_id}/cancel")
async def cancel(project_id: str, _: str = Depends(require_admin)):
    return _act(service.cancel, project_id)


@admin_routes.delete("/api/projects/{project_id}")
async def delete(project_id: str, user: str = Depends(require_admin)):
    service.delete(_id(project_id))
    store.event("INFO", f"Progetto {project_id} eliminato da {user}", "projects")
    return {"ok": True}


@public_routes.post("/api/projects/{project_id}/control/{action}")
async def display_control(project_id: str, action: str, request: Request):
    require_display(request, "Solo dal display")
    handler = DISPLAY_ACTIONS.get(action)
    if handler is None:
        raise HTTPException(404, "Azione sconosciuta")
    store.event("INFO", f"Progetto {project_id}: {action} dal display", "projects")
    return _act(handler, project_id)
