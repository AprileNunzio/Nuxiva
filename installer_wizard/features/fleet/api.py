from fastapi import APIRouter, Depends, HTTPException, Request

from access import require_admin
from features.fleet import catalog
from features.fleet.model import CATEGORIES, DEFAULT_LIMIT, KINDS, LINK_KINDS, ORIGINS, STATES, FleetError, clean_text
from features.fleet.service import fleet
from features.fleet.store import Filter

public_routes = APIRouter()
admin_routes = APIRouter()
PREFIX_MAX = 80


async def _body(request: Request) -> dict:
    try:
        body = await request.json()
    except ValueError:
        raise HTTPException(400, "invalid_body")
    if not isinstance(body, dict):
        raise HTTPException(400, "invalid_body")
    return body


def _fail(error: FleetError) -> HTTPException:
    return HTTPException(error.status, error.code)


def _filter(state: str, kind: str, category: str, origin: str, q: str, tool: str, widget: str) -> Filter:
    for value, options in ((state, STATES), (kind, KINDS), (category, CATEGORIES), (origin, ORIGINS)):
        if value and value not in options:
            raise HTTPException(400, "invalid_filter")
    return Filter(state, kind, category, origin, clean_text(q, PREFIX_MAX), clean_text(tool, 64), clean_text(widget, 64))


@admin_routes.get("/api/fleet/summary")
async def summary(_: str = Depends(require_admin)):
    return fleet.store.summary()


@admin_routes.get("/api/fleet/agents")
async def agents(cursor: str = "", limit: int = DEFAULT_LIMIT, state: str = "", kind: str = "", category: str = "", origin: str = "",
                 q: str = "", tool: str = "", widget: str = "", _: str = Depends(require_admin)):
    flt = _filter(state, kind, category, origin, q, tool, widget)
    try:
        return fleet.store.list(flt, cursor, limit)
    except FleetError as error:
        raise _fail(error)


@admin_routes.get("/api/fleet/agents/{agent_id}")
async def agent(agent_id: str, _: str = Depends(require_admin)):
    try:
        return fleet.detail(agent_id)
    except FleetError as error:
        raise _fail(error)


@admin_routes.post("/api/fleet/agents")
async def create(request: Request, user: str = Depends(require_admin)):
    body = await _body(request)
    try:
        return fleet.create(body, "user", user)
    except FleetError as error:
        raise _fail(error)


@admin_routes.put("/api/fleet/agents/{agent_id}")
async def update(agent_id: str, request: Request, user: str = Depends(require_admin)):
    body = await _body(request)
    try:
        return fleet.update(agent_id, body, user)
    except FleetError as error:
        raise _fail(error)


@admin_routes.delete("/api/fleet/agents/{agent_id}")
async def remove(agent_id: str, user: str = Depends(require_admin)):
    try:
        fleet.delete(agent_id, user)
    except FleetError as error:
        raise _fail(error)
    return {"ok": True}


@admin_routes.post("/api/fleet/agents/{agent_id}/links")
async def attach(agent_id: str, request: Request, user: str = Depends(require_admin)):
    body = await _body(request)
    refs = body.get("refs")
    if body.get("kind") not in LINK_KINDS or not isinstance(refs, list) or not all(isinstance(ref, str) for ref in refs):
        raise HTTPException(400, "invalid_body")
    try:
        return fleet.link(agent_id, body["kind"], refs, user)
    except FleetError as error:
        raise _fail(error)


@admin_routes.delete("/api/fleet/agents/{agent_id}/links/{kind}/{ref}")
async def detach(agent_id: str, kind: str, ref: str, user: str = Depends(require_admin)):
    try:
        return fleet.unlink(agent_id, kind, ref, user)
    except FleetError as error:
        raise _fail(error)


@admin_routes.post("/api/fleet/bulk/state")
async def bulk_state(request: Request, user: str = Depends(require_admin)):
    body = await _body(request)
    flt = _filter(str(body.get("from_state", "")), str(body.get("kind", "")), str(body.get("category", "")), str(body.get("origin", "")),
                  str(body.get("q", "")), str(body.get("tool", "")), str(body.get("widget", "")))
    try:
        return fleet.bulk_state(flt, str(body.get("state", "")), user)
    except FleetError as error:
        raise _fail(error)


@admin_routes.get("/api/fleet/catalog")
async def available(kind: str, q: str = "", limit: int = 50, _: str = Depends(require_admin)):
    if kind not in LINK_KINDS:
        raise HTTPException(400, "invalid_filter")
    query = clean_text(q, PREFIX_MAX)
    return {"items": catalog.tools(query, limit) if kind == "tool" else catalog.widgets(query, limit)}


@admin_routes.post("/api/fleet/suggest")
async def suggest(request: Request, _: str = Depends(require_admin)):
    body = await _body(request)
    return catalog.suggest(clean_text(body.get("purpose"), 400))
