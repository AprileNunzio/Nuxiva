import json

from fastapi import APIRouter, Depends, HTTPException, Request

from access import require_admin
from features.nodes.registry import registry
from features.people import connectors, people
from features.people.fingerprint import local
from features.people.fingerprint.model import FINGERS
from features.people.fingerprint.readers import readers
from features.people.fingerprint.service import service
from features.people.fingerprint.store import bindings
from features.people.vitals.service import RateLimit
from state import store

admin_routes = APIRouter()
public_routes = APIRouter()
NODE_BODY = 16384
limit = RateLimit(120, 60.0)


async def _json(request: Request, size: int) -> dict:
    raw = await request.body()
    if len(raw) > size:
        raise HTTPException(413, "Richiesta troppo grande")
    try:
        body = json.loads(raw)
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


def person_status(slug: str) -> dict:
    state = service.person_state(slug)
    return {"available": True, "linked": bool(state["fingers"]), "enabled": state["enabled"],
            "readers": sum(1 for r in state["readers"] if r["online"])}


connectors.register("fingerprint", "Impronte digitali", "fingerprint", person_status)


@public_routes.post("/api/fingerprint/node")
async def fingerprint_node(request: Request):
    bearer = request.headers.get("authorization", "").removeprefix("Bearer ").strip()
    try:
        node = registry.authenticate(request.headers.get("x-nuxiva-node", ""), bearer)
    except PermissionError as exc:
        raise HTTPException(401, str(exc))
    if not limit.allow(node["id"]):
        raise HTTPException(429, "Troppe richieste")
    return service.node_report(node["id"], await _json(request, NODE_BODY))


@admin_routes.get("/api/fingerprint/readers")
async def fingerprint_readers(_: str = Depends(require_admin)):
    await local.discover()
    return {"readers": readers.listing()}


@admin_routes.get("/api/people/{slug}/fingerprint")
async def person_fingerprint(slug: str, _: str = Depends(require_admin)):
    _person(slug)
    await local.discover()
    return {**service.person_state(slug), "all_fingers": list(FINGERS)}


@admin_routes.put("/api/people/{slug}/fingerprint")
async def person_fingerprint_toggle(slug: str, request: Request, user: str = Depends(require_admin)):
    _person(slug)
    body = await _json(request, 256)
    if not isinstance(body.get("enabled"), bool):
        raise HTTPException(400, "Richiesta non valida")
    bindings.set_enabled(slug, body["enabled"])
    store.event("INFO", f"Impronte digitali {'attivate' if body['enabled'] else 'disattivate'} per {slug} da {user}", "fingerprint")
    return {"enabled": body["enabled"]}


@admin_routes.post("/api/people/{slug}/fingerprint/enroll")
async def person_fingerprint_enroll(slug: str, request: Request, user: str = Depends(require_admin)):
    _person(slug)
    body = await _json(request, 512)
    try:
        started = service.start_enroll(slug, str(body.get("finger", "")), str(body.get("reader", "")))
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    store.event("INFO", f"Registrazione impronta avviata per {slug} da {user}", "fingerprint")
    return {"expires_in": started["expires_in"], "reader": started["reader"]}


@admin_routes.delete("/api/people/{slug}/fingerprint/enroll")
async def person_fingerprint_cancel(slug: str, _: str = Depends(require_admin)):
    _person(slug)
    service.cancel_enroll(slug)
    return {"cancelled": True}


@admin_routes.delete("/api/people/{slug}/fingerprint")
async def person_fingerprint_forget(slug: str, finger: str = "", user: str = Depends(require_admin)):
    _person(slug)
    if finger and finger not in FINGERS:
        raise HTTPException(400, "Dito non valido")
    removed = bindings.forget(slug, finger)
    store.event("INFO", f"Impronte di {slug} eliminate ({removed}) da {user}", "fingerprint")
    return {"removed": removed}
