import re

from fastapi import APIRouter, Depends, HTTPException, Request

from access import require_admin
from tasks import background

from features.agency.client import AgencyRejected, AgencyUnavailable
from features.agency.foresight import service
from features.agency.words import lang_of, word

routes = APIRouter()
SIMULATION_ID = re.compile(r"[a-z0-9][a-z0-9_-]{0,63}")
CODES = ("unavailable", "invalid", "not_found", "brain", "material", "question", "empty_world", "event",
         "message", "busy", "exists", "too_many", "sealed")
STATUS = {"not_found": 404, "exists": 409, "too_many": 429, "busy": 409, "unavailable": 503, "sealed": 500}


def _lang(request: Request) -> str:
    from features.locale.api import page_language
    return lang_of(page_language(request, True))


def _fail(request: Request, code: str):
    key = code if code in CODES else "invalid"
    raise HTTPException(STATUS.get(key, 400), {"code": key, "message": word(_lang(request), "foresight_errors", key)})


def _id(request: Request, simulation_id: str) -> str:
    if not SIMULATION_ID.fullmatch(simulation_id):
        _fail(request, "not_found")
    return simulation_id


async def _guard(request: Request, call):
    try:
        return await call
    except AgencyUnavailable:
        _fail(request, "unavailable")
    except AgencyRejected as exc:
        _fail(request, exc.code)
    except service.ForesightFailure as exc:
        _fail(request, exc.code)


async def _body(request: Request) -> dict:
    try:
        body = await request.json()
    except ValueError:
        _fail(request, "invalid")
    if not isinstance(body, dict):
        _fail(request, "invalid")
    return body


@routes.get("/api/agency/foresight")
async def overview(request: Request, _: str = Depends(require_admin)):
    return {"simulations": await _guard(request, service.overview())}


@routes.post("/api/agency/foresight", status_code=202)
async def create(request: Request, _: str = Depends(require_admin)):
    body = await _body(request)
    material, question = body.get("material"), body.get("question")
    if not isinstance(material, str) or len(material.strip()) < service.MATERIAL_MIN:
        _fail(request, "material")
    if not isinstance(question, str) or len(question.strip()) < service.QUESTION_MIN:
        _fail(request, "question")
    background(service.launch(material, question, _lang(request), body.get("population"), body.get("rounds")))
    return {"accepted": True}


@routes.get("/api/agency/foresight/{simulation_id}")
async def detail(simulation_id: str, request: Request, _: str = Depends(require_admin)):
    return await _guard(request, service.detail(_id(request, simulation_id)))


@routes.post("/api/agency/foresight/{simulation_id}/run", status_code=202)
async def run(simulation_id: str, request: Request, _: str = Depends(require_admin)):
    background(service.resume(_id(request, simulation_id)))
    return {"accepted": True}


@routes.post("/api/agency/foresight/{simulation_id}/events")
async def inject(simulation_id: str, request: Request, _: str = Depends(require_admin)):
    body = await _body(request)
    return await _guard(request, service.inject(_id(request, simulation_id), body))


@routes.post("/api/agency/foresight/{simulation_id}/ensemble")
async def ensemble(simulation_id: str, request: Request, _: str = Depends(require_admin)):
    body = await _body(request)
    return await _guard(request, service.ensemble(_id(request, simulation_id), body.get("runs")))


@routes.post("/api/agency/foresight/{simulation_id}/narrative")
async def narrate(simulation_id: str, request: Request, _: str = Depends(require_admin)):
    return await _guard(request, service.narrate(_id(request, simulation_id), _lang(request)))


@routes.get("/api/agency/foresight/{simulation_id}/agents/{agent_key}")
async def agent(simulation_id: str, agent_key: str, request: Request, _: str = Depends(require_admin)):
    return await _guard(request, service.agent(_id(request, simulation_id), agent_key))


@routes.post("/api/agency/foresight/{simulation_id}/agents/{agent_key}/chat")
async def chat(simulation_id: str, agent_key: str, request: Request, _: str = Depends(require_admin)):
    body = await _body(request)
    message = body.get("message")
    if not isinstance(message, str):
        _fail(request, "message")
    return await _guard(request, service.chat(_id(request, simulation_id), agent_key, message, _lang(request)))


@routes.delete("/api/agency/foresight/{simulation_id}")
async def delete(simulation_id: str, request: Request, _: str = Depends(require_admin)):
    return await _guard(request, service.delete(_id(request, simulation_id)))
