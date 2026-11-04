from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from access import NO_CACHE, require_admin
from features.tasks import sources
from features.tasks.registry import ID_RE, registry

admin_routes = APIRouter(prefix="/api/tasks", tags=["Attività"])


class AnswerIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action: str = Field(default="", max_length=20)


async def snapshot() -> dict:
    rows = sorted([*registry.rows(), *await sources.projects()], key=lambda r: r["updated"], reverse=True)
    active = [r for r in rows if r["state"] in ("queued", "running")]
    waiting = [r for r in rows if r["state"] == "done" and r.get("offer") and not r.get("answered")]
    return {"tasks": rows[:60], "active": len(active), "waiting": len(waiting)}


@admin_routes.get("")
async def overview(_: str = Depends(require_admin)):
    return JSONResponse(await snapshot(), headers=NO_CACHE)


@admin_routes.post("/{task_id}/answer")
async def answer(task_id: str, body: AnswerIn, _: str = Depends(require_admin)):
    if not ID_RE.fullmatch(task_id):
        raise HTTPException(404, "task_unknown")
    row = registry.answer(task_id)
    if row is None:
        raise HTTPException(404, "task_unknown")
    return JSONResponse({"task": row, "action": body.action}, headers=NO_CACHE)


@admin_routes.post("/{task_id}/cancel")
async def cancel(task_id: str, _: str = Depends(require_admin)):
    if task_id.startswith(sources.PREFIX):
        return await _cancel_project(task_id.removeprefix(sources.PREFIX))
    if not ID_RE.fullmatch(task_id):
        raise HTTPException(404, "task_unknown")
    if not registry.cancel(task_id):
        raise HTTPException(409, "not_active")
    return {"ok": True}


async def _cancel_project(project_id: str) -> dict:
    from features.agency import service
    from features.agency.client import AgencyRejected, AgencyUnavailable
    from features.agency.memory import ID
    if not ID.fullmatch(project_id):
        raise HTTPException(404, "task_unknown")
    try:
        await service.control(project_id, "cancel")
    except AgencyUnavailable as exc:
        raise HTTPException(503, "unavailable") from exc
    except AgencyRejected as exc:
        raise HTTPException(404 if exc.code == "not_found" else 409, "not_active") from exc
    return {"ok": True}
