import json
import time

from fastapi import APIRouter, Depends, HTTPException, Request

from access import require_admin
from features.nodes.registry import registry
from features.people import connectors, people
from features.people.vitals import service
from features.people.vitals.book import book
from features.people.vitals.journal import journal
from features.people.vitals.live import live
from features.people.vitals.nearby import SEARCH_SECONDS, nearby
from features.people.vitals.pairing import pairing
from state import store

admin_routes = APIRouter()
public_routes = APIRouter()
PUSH_BODY = 8192
NODE_BODY = 32768
PUSH_SAMPLES = 60


async def _json(request: Request, limit: int) -> dict:
    raw = await request.body()
    if len(raw) > limit:
        raise HTTPException(413, "Richiesta troppo grande")
    try:
        body = json.loads(raw)
    except (UnicodeDecodeError, ValueError):
        raise HTTPException(400, "Richiesta non valida")
    if not isinstance(body, dict):
        raise HTTPException(400, "Richiesta non valida")
    return body


def _bearer(request: Request) -> str:
    return request.headers.get("authorization", "").removeprefix("Bearer ").strip()


def _person(slug: str) -> dict:
    profile = people.load(slug)
    if not profile:
        raise HTTPException(404, "Persona non trovata")
    return profile


def person_status(slug: str) -> dict:
    devices = book.of(slug)
    snap = service.snapshot(slug)
    return {"available": True, "linked": bool(devices) or snap["cloud"]["ready"], "devices": len(devices), "live": bool(snap["values"]),
            "cloud": snap["cloud"]["ready"]}


connectors.register("vitals", "Parametri vitali", "heart", person_status)


@public_routes.post("/api/vitals/push")
async def vitals_push(request: Request):
    device = book.by_token(_bearer(request))
    if not device or device["kind"] == "ble":
        raise HTTPException(401, "Dispositivo non autorizzato")
    if not service.push_limit.allow(device["id"]):
        raise HTTPException(429, "Troppe richieste")
    body = await _json(request, PUSH_BODY)
    samples = body.get("samples")
    if not isinstance(samples, list) or len(samples) > PUSH_SAMPLES:
        raise HTTPException(400, "Richiesta non valida")
    book.touch(device)
    return service.ingest(device["slug"], samples, device["id"], device["kind"])


@public_routes.post("/api/vitals/node")
async def vitals_node(request: Request):
    try:
        node = registry.authenticate(request.headers.get("x-nuxiva-node", ""), _bearer(request))
    except PermissionError as exc:
        raise HTTPException(401, str(exc))
    if not service.node_limit.allow(node["id"]):
        raise HTTPException(429, "Troppe richieste")
    return service.node_report(node["id"], await _json(request, NODE_BODY))


@public_routes.post("/api/vitals/pair")
async def vitals_pair(request: Request):
    ip = request.client.host if request.client else "?"
    if not service.pair_limit.allow(ip):
        raise HTTPException(429, "Troppi tentativi: riprova tra qualche minuto")
    body = await _json(request, 512)
    slug = pairing.redeem(str(body.get("code", ""))[:12])
    if not slug or not people.load(slug):
        raise HTTPException(403, "Codice non valido o scaduto")
    try:
        device, token = book.add(slug, "phone", str(body.get("label", "")) or "Telefono")
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    journal.add(slug, "info", "phone_paired", {"device": device["label"]})
    return {"token": token}


@admin_routes.get("/api/people/{slug}/vitals")
async def person_vitals(slug: str, _: str = Depends(require_admin)):
    _person(slug)
    now = time.time()
    snap = service.snapshot(slug, now)
    return {"devices": service.devices_view(slug, snap["values"], now), "units": service.units(), "nodes": service.capable_nodes(now), **snap}


@admin_routes.post("/api/people/{slug}/vitals/search")
async def person_vitals_search(slug: str, _: str = Depends(require_admin)):
    _person(slug)
    nodes = service.capable_nodes()
    nearby.start(slug)
    journal.add(slug, "info" if nodes else "warn", "search_started" if nodes else "search_no_nodes", {"nodes": len(nodes)})
    return {"nodes": nodes, "seconds": int(SEARCH_SECONDS)}


@admin_routes.get("/api/people/{slug}/vitals/nearby")
async def person_vitals_nearby(slug: str, _: str = Depends(require_admin)):
    _person(slug)
    taken = {d["address"] for d in book.all_devices() if d.get("address")}
    return {"active": nearby.searching(slug), "nodes": service.capable_nodes(), "found": nearby.listing(taken)}


@admin_routes.get("/api/people/{slug}/vitals/log")
async def person_vitals_log(slug: str, _: str = Depends(require_admin)):
    _person(slug)
    return {"entries": journal.entries(slug)}


@admin_routes.post("/api/people/{slug}/vitals/phone-code")
async def person_vitals_phone_code(slug: str, _: str = Depends(require_admin)):
    _person(slug)
    journal.add(slug, "info", "code_created")
    return pairing.create(slug)


@admin_routes.post("/api/people/{slug}/vitals/devices")
async def person_vitals_add(slug: str, request: Request, user: str = Depends(require_admin)):
    _person(slug)
    body = await _json(request, 1024)
    try:
        address = body.get("address", "")
        if body.get("ref"):
            address = nearby.resolve(str(body["ref"])[:16])
            if not address:
                raise ValueError("Dispositivo non più vicino: ripeti la ricerca")
        device, token = book.add(slug, str(body.get("kind", "")), body.get("label", ""), address)
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    store.event("INFO", f"Dispositivo vitali '{device['label']}' aggiunto a {slug} da {user}", "people")
    journal.add(slug, "info", "device_added", {"device": device["label"]})
    nearby.stop(slug)
    return {"device": device, "token": token}


@admin_routes.post("/api/people/{slug}/vitals/devices/{device_id}/token")
async def person_vitals_rotate(slug: str, device_id: str, user: str = Depends(require_admin)):
    _person(slug)
    try:
        token = book.rotate(slug, device_id)
    except KeyError:
        raise HTTPException(404, "Dispositivo non trovato")
    store.event("INFO", f"Chiave del dispositivo vitali {device_id} rigenerata per {slug} da {user}", "people")
    journal.add(slug, "info", "key_renewed")
    return {"token": token}


@admin_routes.post("/api/people/{slug}/vitals/devices/{device_id}/{action}")
async def person_vitals_switch(slug: str, device_id: str, action: str, user: str = Depends(require_admin)):
    _person(slug)
    if action not in ("disconnect", "reconnect"):
        raise HTTPException(404, "Azione sconosciuta")
    try:
        device = book.set_enabled(slug, device_id, action == "reconnect")
    except KeyError:
        raise HTTPException(404, "Dispositivo non trovato")
    service.drop_device(book.raw(device_id) or device)
    journal.add(slug, "info", "device_on" if action == "reconnect" else "device_off", {"device": device["label"]})
    store.event("INFO", f"Dispositivo vitali {device_id} {'ricollegato' if action == 'reconnect' else 'scollegato'} per {slug} da {user}", "people")
    return {"device": device}


@admin_routes.delete("/api/people/{slug}/vitals/devices/{device_id}")
async def person_vitals_remove(slug: str, device_id: str, user: str = Depends(require_admin)):
    _person(slug)
    if not book.remove(slug, device_id):
        raise HTTPException(404, "Dispositivo non trovato")
    live.forget(slug)
    store.event("INFO", f"Dispositivo vitali {device_id} rimosso da {slug} da {user}", "people")
    journal.add(slug, "info", "device_removed")
    return {"ok": True}
