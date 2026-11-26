import json
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from access import NO_CACHE, require_admin
from agenti.authz.access_control import require_permission
from agenti.reasoning import sources, state, traces

admin_routes = APIRouter(prefix="/api/v5/reasoning", tags=["Reasoning"], dependencies=[Depends(require_admin)])
READ, MANAGE = ["reasoning.read"], ["reasoning.manage"]
NODE = "local"


class ModeBody(BaseModel):
    mode: Literal["off", "shadow", "active"]
    force: bool = False


class GateBody(BaseModel):
    min_days: int = Field(7, ge=1, le=30)
    min_samples: int = Field(200, ge=1, le=1_000_000)
    min_agreement_bps: int = Field(9500, ge=0, le=10_000)
    max_invalid_bps: int = Field(500, ge=0, le=10_000)
    max_wrong_action: int = Field(0, ge=0, le=1_000)


class ConfigBody(BaseModel):
    retrieve_limit: int = Field(8, ge=1, le=24)
    max_corrections: int = Field(1, ge=0, le=3)
    cache_capacity: int = Field(512, ge=1, le=100_000)
    cache_ttl_ms: int = Field(86_400_000, ge=1_000, le=2_592_000_000)
    understand_threshold_bps: int = Field(8500, ge=0, le=10_000)
    gate: GateBody = Field(default_factory=GateBody)


def respond(payload) -> JSONResponse:
    return JSONResponse(payload, headers=NO_CACHE)


def allow(user: str, capability: str) -> None:
    require_permission(user, capability, NODE)


def engine():
    try:
        return state.engine()
    except state.Unavailable as exc:
        raise HTTPException(503, "native_unavailable") from exc


def snapshot() -> dict:
    current = engine()
    inventory = sources.sync()
    return {**json.loads(current.status(state.now_ms())), "config": json.loads(current.config()),
            "inventory": {"count": inventory["count"], "inferred": inventory["inferred"]}, "emergency_off": state.emergency_off()}


@admin_routes.get("/status", openapi_extra={"x-nuxiva-capabilities": READ})
async def status(user: str = Depends(require_admin)):
    allow(user, "reasoning.read")
    if not state.ready():
        return respond({"native": False})
    return respond({"native": True, **snapshot()})


@admin_routes.get("/traces", openapi_extra={"x-nuxiva-capabilities": READ})
async def recent(limit: int = Query(50, ge=1, le=traces.MAX_TRACES), user: str = Depends(require_admin)):
    allow(user, "reasoning.read")
    return respond({"traces": traces.recent(limit)})


@admin_routes.post("/mode", openapi_extra={"x-nuxiva-capabilities": MANAGE})
async def set_mode(body: ModeBody, user: str = Depends(require_admin)):
    allow(user, "reasoning.manage")
    if body.mode != "off" and state.emergency_off():
        raise HTTPException(409, "reason.mode.emergency_off")
    try:
        engine().set_mode(body.mode, body.force, state.now_ms())
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc
    state.save()
    return respond(snapshot())


@admin_routes.post("/kill", openapi_extra={"x-nuxiva-capabilities": MANAGE})
async def kill(user: str = Depends(require_admin)):
    allow(user, "reasoning.manage")
    engine().kill()
    state.save()
    return respond(snapshot())


@admin_routes.put("/config", openapi_extra={"x-nuxiva-capabilities": MANAGE})
async def configure(body: ConfigBody, user: str = Depends(require_admin)):
    allow(user, "reasoning.manage")
    engine()
    try:
        state.save_config(body.model_dump_json())
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    return respond(snapshot())


@admin_routes.post("/ledger/reset", openapi_extra={"x-nuxiva-capabilities": MANAGE})
async def reset_ledger(user: str = Depends(require_admin)):
    allow(user, "reasoning.manage")
    engine().reset_ledger()
    state.save()
    return respond(snapshot())


@admin_routes.post("/inventory/refresh", openapi_extra={"x-nuxiva-capabilities": MANAGE})
async def refresh(user: str = Depends(require_admin)):
    allow(user, "reasoning.manage")
    engine()
    sources.sync(force=True)
    return respond(snapshot())


class FeedbackBody(BaseModel):
    wrong_action: bool


@admin_routes.post("/feedback", openapi_extra={"x-nuxiva-capabilities": MANAGE})
async def feedback(body: FeedbackBody, user: str = Depends(require_admin)):
    allow(user, "reasoning.manage")
    if body.wrong_action:
        engine().record(json.dumps({"valid": True, "wrong_action": True}), state.now_ms())
        state.save()
    return respond(snapshot())
