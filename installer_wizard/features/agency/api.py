import re

from fastapi import APIRouter, Depends, HTTPException, Request

from access import require_admin
from tasks import background

from features.agency import service
from features.agency.client import AgencyRejected, AgencyUnavailable
from features.agency.words import lang_of, word

admin_routes = APIRouter()
PROJECT_ID = re.compile(r"[a-z0-9][a-z0-9_-]{0,63}")
STATUS = {"not_found": 404, "invalid": 400, "bad_request": 400, "plan": 400, "exists": 409, "too_many": 429}


def _lang(request: Request) -> str:
    from features.locale.api import page_language
    return lang_of(page_language(request, True))


def _fail(request: Request, code: str, status: int):
    key = code if code in ("unavailable", "invalid", "not_found", "brain", "empty_plan", "goal") else "invalid"
    raise HTTPException(status, {"code": key, "message": word(_lang(request), "errors", key)})


def _project(request: Request, project_id: str) -> str:
    if not PROJECT_ID.fullmatch(project_id):
        _fail(request, "not_found", 404)
    return project_id


async def _guard(request: Request, call):
    try:
        return await call
    except AgencyUnavailable:
        _fail(request, "unavailable", 503)
    except AgencyRejected as exc:
        _fail(request, exc.code, STATUS.get(exc.code, 400))
    except service.AgencyFailure as exc:
        _fail(request, exc.code, 400)


@admin_routes.get("/api/agency")
async def overview(request: Request, _: str = Depends(require_admin)):
    return await _guard(request, service.overview())


@admin_routes.get("/api/agency/projects/{project_id}")
async def detail(project_id: str, request: Request, _: str = Depends(require_admin)):
    return await _guard(request, service.detail(_project(request, project_id)))


@admin_routes.post("/api/agency/projects", status_code=202)
async def create(request: Request, _: str = Depends(require_admin)):
    try:
        body = await request.json()
    except ValueError:
        _fail(request, "invalid", 400)
    goal = body.get("goal") if isinstance(body, dict) else None
    if not isinstance(goal, str) or len(goal.strip()) < service.GOAL_MIN or len(goal) > service.GOAL_MAX:
        _fail(request, "goal", 400)
    background(service.launch(goal, _lang(request)))
    return {"accepted": True}


@admin_routes.post("/api/agency/projects/{project_id}/{action}")
async def control(project_id: str, action: str, request: Request, _: str = Depends(require_admin)):
    if action not in service.CONTROLS:
        _fail(request, "invalid", 400)
    return await _guard(request, service.control(_project(request, project_id), action))
