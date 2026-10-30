import json
import time

from access import require_admin
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response
from state import store

from features.nodes import trust
from features.nodes.enrollment import EnrollmentError, tokens
from features.secure import api as secure
from features.nodes.registry import TYPES, clean_id, registry

ENROLL_TYPES = set(TYPES) - {"server"}

public_routes = APIRouter()
admin_routes = APIRouter()
_failures: dict[str, list[float]] = {}
WINDOW = 300
LIMIT = 5


def _ip(request: Request) -> str:
    return request.client.host if request.client else "?"


def _limited(ip: str) -> bool:
    recent = [t for t in _failures.get(ip, []) if time.time() - t < WINDOW]
    _failures[ip] = recent
    return len(recent) >= LIMIT


def _fail(ip: str) -> None:
    _failures.setdefault(ip, []).append(time.time())


@public_routes.post("/api/nodes/enroll")
async def node_enroll(request: Request):
    ip = _ip(request)
    if _limited(ip):
        raise HTTPException(429, "rate_limited")
    if int(request.headers.get("content-length") or 0) > 4096:
        raise HTTPException(413, "payload_too_large")
    body = await request.json()
    if not isinstance(body, dict):
        raise HTTPException(400, "invalid_request")
    try:
        node_id = clean_id(body.get("id"))
    except ValueError:
        raise HTTPException(400, "enroll_invalid_node_id")
    if node_id in registry.data["nodes"]:
        raise HTTPException(409, "enroll_node_exists")
    try:
        digest = tokens.verify(str(body.get("token") or ""))
        kind = body.get("type") if body.get("type") in ENROLL_TYPES else "desktop"
        node_token = registry.pair(registry.new_code()["code"], node_id, {**body, "type": kind})
    except EnrollmentError as exc:
        _fail(ip)
        store.event("WARN", f"Iscrizione nodo rifiutata da {ip}", "nodes")
        raise HTTPException(403, exc.code)
    except ValueError:
        raise HTTPException(400, "enroll_rejected")
    tokens.burn(digest)
    store.event("INFO", f"Nodo {node_id} iscritto con token monouso ({ip})", "nodes")
    return {"token": node_token, "heartbeat": 30}


@admin_routes.post("/api/nodes/satellite-enrollment")
async def satellite_enrollment(request: Request, user: str = Depends(require_admin)):
    origin = trust.https_origin(request.url.hostname, secure._active["port"])
    if not origin:
        raise HTTPException(409, "enroll_https_unavailable")
    pin = trust.ca_pin()
    if not pin:
        raise HTTPException(409, "enroll_ca_missing")
    try:
        token, expires = tokens.issue()
    except EnrollmentError as exc:
        raise HTTPException(429, exc.code)
    store.event("INFO", f"Iscrizione monouso per un satellite generata da {user}", "nodes")
    body = json.dumps({"server": origin, "token": token, "pin": pin, "expires": int(expires)})
    return Response(body, media_type="application/json",
                    headers={"Content-Disposition": "attachment; filename=nuxiva-satellite-enroll.json", "Cache-Control": "no-store"})
