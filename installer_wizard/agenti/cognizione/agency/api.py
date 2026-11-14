import re

from fastapi import APIRouter, Depends, HTTPException, Request

from access import require_admin, require_display
from state import store
from tasks import background

from agenti.agency import board, service
from agenti.agency.client import AgencyRejected, AgencyUnavailable
from agenti.agency.foresight.api import routes as foresight_routes
from agenti.agency.forge.guard import NAME, ForgeRejected
from agenti.agency.forge.registry import ACTIVE, RETIRED, registry
from agenti.agency.words import lang_of, word

admin_routes = APIRouter()
public_routes = APIRouter()
admin_routes.include_router(foresight_routes)
PROJECT_ID = re.compile(r"[a-z0-9][a-z0-9_-]{0,63}")
BOARD_CONTROLS = ("pause", "resume")
TOOL_ACTIONS = {"retire": RETIRED, "restore": ACTIVE}
STATUS = {"not_found": 404, "invalid": 400, "bad_request": 400, "plan": 400, "exists": 409, "too_many": 429}


def _lang(request: Request) -> str:
    from agenti.locale.api import page_language
    return lang_of(page_language(request, True))


def _fail(request: Request, code: str, status: int):
    key = code if code in ("unavailable", "invalid", "not_found", "brain", "empty_plan", "goal", "tool_not_found", "tool_limit", "confirm", "delete_blocked", "archive_blocked") else "invalid"
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


async def _accept(request: Request) -> dict:
    try:
        body = await request.json()
    except ValueError:
        _fail(request, "invalid", 400)
    goal = body.get("goal") if isinstance(body, dict) else None
    if not isinstance(goal, str) or len(goal.strip()) < service.GOAL_MIN or len(goal) > service.GOAL_MAX:
        _fail(request, "goal", 400)
    background(service.launch(goal, _lang(request)))
    return {"accepted": True}


@admin_routes.post("/api/agency/projects", status_code=202)
async def create(request: Request, _: str = Depends(require_admin)):
    return await _accept(request)


async def _body(request: Request) -> dict:
    try:
        body = await request.json()
    except ValueError:
        _fail(request, "invalid", 400)
    if not isinstance(body, dict):
        _fail(request, "invalid", 400)
    return body


def _audit(user: str, project_id: str, what: str) -> None:
    store.event("INFO", f"Agency project {project_id}: {what} by {user}", "agency")


@admin_routes.patch("/api/agency/projects/{project_id}")
async def rename(project_id: str, request: Request, user: str = Depends(require_admin)):
    pid = _project(request, project_id)
    body = await _body(request)
    title = body.get("title")
    if not isinstance(title, str):
        _fail(request, "invalid", 400)
    result = await _guard(request, service.rename(pid, title))
    _audit(user, pid, "renamed")
    return result


@admin_routes.post("/api/agency/projects/{project_id}/archive")
async def archive(project_id: str, request: Request, user: str = Depends(require_admin)):
    pid = _project(request, project_id)
    try:
        result = await service.archive(pid, True)
    except AgencyRejected as exc:
        _fail(request, "archive_blocked" if exc.code == "invalid" else exc.code, 409)
    except (AgencyUnavailable, service.AgencyFailure):
        _fail(request, "unavailable", 503)
    _audit(user, pid, "archived")
    return result


@admin_routes.post("/api/agency/projects/{project_id}/unarchive")
async def unarchive(project_id: str, request: Request, user: str = Depends(require_admin)):
    pid = _project(request, project_id)
    result = await _guard(request, service.archive(pid, False))
    _audit(user, pid, "restored from archive")
    return result


@admin_routes.put("/api/agency/projects/{project_id}/agents")
async def assign(project_id: str, request: Request, user: str = Depends(require_admin)):
    pid = _project(request, project_id)
    body = await _body(request)
    result = await _guard(request, service.assign(pid, body.get("agents")))
    _audit(user, pid, "agents reassigned")
    return result


@admin_routes.delete("/api/agency/projects/{project_id}")
async def remove(project_id: str, request: Request, user: str = Depends(require_admin)):
    pid = _project(request, project_id)
    body = await _body(request)
    confirm = body.get("confirm")
    if not isinstance(confirm, str):
        _fail(request, "confirm", 400)
    try:
        result = await service.delete(pid, confirm)
    except service.AgencyFailure as exc:
        _fail(request, exc.code, 400)
    except AgencyRejected as exc:
        _fail(request, "delete_blocked" if exc.code == "bad_request" else exc.code, 409)
    except AgencyUnavailable:
        _fail(request, "unavailable", 503)
    _audit(user, pid, "deleted")
    return result


@admin_routes.post("/api/agency/projects/{project_id}/tasks/{task_id}/{action}")
async def review(project_id: str, task_id: str, action: str, request: Request, user: str = Depends(require_admin)):
    pid = _project(request, project_id)
    tid = _project(request, task_id)
    if action not in service.TASK_ACTIONS:
        _fail(request, "invalid", 400)
    try:
        body = await request.json()
    except ValueError:
        body = {}
    feedback = body.get("feedback", "") if isinstance(body, dict) else ""
    result = await _guard(request, service.review(pid, tid, action, feedback if isinstance(feedback, str) else ""))
    _audit(user, pid, f"task {tid} {action}")
    return result


@admin_routes.post("/api/agency/projects/{project_id}/{action}")
async def control(project_id: str, action: str, request: Request, user: str = Depends(require_admin)):
    if action not in service.CONTROLS:
        _fail(request, "invalid", 400)
    pid = _project(request, project_id)
    result = await _guard(request, service.control(pid, action))
    _audit(user, pid, action)
    return result


def _tool(request: Request, tool_name: str):
    tool = registry.get(tool_name) if NAME.fullmatch(tool_name) else None
    if tool is None:
        _fail(request, "tool_not_found", 404)
    return tool


@admin_routes.get("/api/agency/tools")
async def tools_list(_: str = Depends(require_admin)):
    return {"tools": [tool.public() for tool in registry.all()]}


@admin_routes.get("/api/agency/tools/{tool_name}")
async def tools_detail(tool_name: str, request: Request, _: str = Depends(require_admin)):
    return _tool(request, tool_name).public(with_code=True)


@admin_routes.post("/api/agency/tools/{tool_name}/{action}")
async def tools_control(tool_name: str, action: str, request: Request, _: str = Depends(require_admin)):
    if action not in TOOL_ACTIONS:
        _fail(request, "invalid", 400)
    _tool(request, tool_name)
    try:
        return registry.set_status(tool_name, TOOL_ACTIONS[action], "admin").public()
    except ForgeRejected:
        _fail(request, "tool_limit", 409)


@admin_routes.delete("/api/agency/tools/{tool_name}")
async def tools_delete(tool_name: str, request: Request, _: str = Depends(require_admin)):
    _tool(request, tool_name)
    registry.delete(tool_name)
    return {"deleted": tool_name}


def _display_write(request: Request) -> None:
    require_display(request)
    if request.headers.get("X-Nuxiva-Request") != "1":
        _fail(request, "invalid", 403)


@public_routes.get("/api/agency/board")
async def board_overview(request: Request):
    require_display(request)
    return await _guard(request, board.overview())


@public_routes.get("/api/agency/board/{project_id}")
async def board_focus(project_id: str, request: Request):
    require_display(request)
    return await _guard(request, board.focus(_project(request, project_id)))


@public_routes.post("/api/agency/board/projects", status_code=202)
async def board_create(request: Request):
    _display_write(request)
    return await _accept(request)


@public_routes.post("/api/agency/board/{project_id}/{action}")
async def board_control(project_id: str, action: str, request: Request):
    _display_write(request)
    if action not in BOARD_CONTROLS:
        _fail(request, "invalid", 400)
    pid = _project(request, project_id)
    await _guard(request, service.control(pid, action))
    return await _guard(request, board.focus(pid))


@public_routes.post("/api/agency/board/{project_id}/tasks/{task_id}/{action}")
async def board_task_action(project_id: str, task_id: str, action: str, request: Request):
    from agenti.agency import office
    _display_write(request)
    pid = _project(request, project_id)
    tid = _project(request, task_id)
    if action not in office.TASK_ACTIONS:
        _fail(request, "invalid", 400)
    try:
        body = await request.json()
    except ValueError:
        body = {}
    await _guard(request, office.task_action(pid, tid, action, body if isinstance(body, dict) else {}))
    return await _guard(request, board.focus(pid))


@public_routes.post("/api/agency/board/{project_id}/questions/{question_id}/answer")
async def board_question_answer(project_id: str, question_id: str, request: Request):
    _display_write(request)
    pid = _project(request, project_id)
    qid = _project(request, question_id)
    try:
        body = await request.json()
    except ValueError:
        _fail(request, "invalid", 400)
    if not isinstance(body, dict):
        _fail(request, "invalid", 400)
    option = str(body.get("option") or "").strip()[:120] or None
    answer_text = str(body.get("answer") or "").strip()[:600] or None
    if not option and not answer_text:
        _fail(request, "invalid", 400)
    await _guard(request, service.answer(pid, qid, option=option, answer_text=answer_text))
    return await _guard(request, board.focus(pid))


@public_routes.get("/api/agency/board/{project_id}/autonomy")
async def board_autonomy_status(project_id: str, request: Request):
    from agenti.agency import autonomy
    require_display(request)
    pid = _project(request, project_id)
    data = await _guard(request, service.detail(pid))
    tasks = data.get("tasks") or []
    evaluations = [autonomy.evaluate(t).to_dict() for t in tasks if isinstance(t, dict)]
    return {
        "project_id": pid,
        "engine": "nuxiva_risk_matrix",
        "evaluations": evaluations,
        "auto_approved": sum(1 for e in evaluations if e["autonomous"]),
        "human_supervision_required": sum(1 for e in evaluations if not e["autonomous"]),
    }


@public_routes.get("/api/agency/board/{project_id}/briefing")
async def board_briefing(project_id: str, request: Request):
    from agenti.agency import proactive
    require_display(request)
    pid = _project(request, project_id)
    data = await _guard(request, service.detail(pid))
    tasks = data.get("tasks") or []
    questions = (data.get("project") or {}).get("questions") or []
    counts = data.get("counts") or {"total": len(tasks), "done": sum(1 for t in tasks if t.get("status") == "done")}
    telemetry = proactive.sample_telemetry()
    insights = proactive.analyze_insights(tasks, questions, telemetry)
    lang = request.query_params.get("lang") or "it"
    title = (data.get("project") or {}).get("title") or "Progetto"
    from agenti.chat.reflex_memory import reflex_memory
    active_prof = reflex_memory.get_profile()
    user_name = request.query_params.get("user") or (active_prof.user_name if active_prof and active_prof.user_name != "user" else None)
    briefing = proactive.generate_briefing(lang, title, counts, insights, user_name=user_name)
    return {
        "project_id": pid,
        "briefing": briefing,
        "insights": [ins.to_dict() for ins in insights],
        "telemetry": telemetry.to_dict(),
    }


@public_routes.get("/api/agency/board/{project_id}/cognition")
async def board_cognition(project_id: str, request: Request):
    from agenti.agency import cognition
    require_display(request)
    pid = _project(request, project_id)
    data = await _guard(request, service.detail(pid))
    project = data.get("project") or {}
    goal = str(project.get("goal") or project.get("title") or "Progetto")
    bp = data.get("blueprint") or {}
    arch = str(bp.get("architecture") or "")
    decisions = [f"{d.get('topic', '')}: {d.get('choice', '')}" for d in (project.get("decisions") or []) if isinstance(d, dict)]
    socratic = cognition.interrogate_goal(goal, decisions)
    specialists = cognition.recruit_specialists(goal, arch)
    return {
        "project_id": pid,
        "socratic": socratic,
        "specialists": specialists,
    }

