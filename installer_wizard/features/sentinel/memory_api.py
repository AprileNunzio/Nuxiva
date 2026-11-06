import json
import re
import threading
import time

from access import NO_CACHE, require_admin
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse

from features.sentinel import memory_people, record
from features.sentinel.journal import SentinelUnavailable
from features.sentinel.memory import memory

routes = APIRouter()
READ = {"x-nuxiva-capabilities": ["sentinel.read"]}
MANAGE = {"x-nuxiva-capabilities": ["sentinel.manage"]}
SLUG = re.compile(r"^[a-z0-9_.-]{1,64}$")
ID = re.compile(r"^[0-9a-f]{16,32}$")
DAY = re.compile(r"^\d{4}-\d{2}-\d{2}$")
AUDIENCES = frozenset({"household", "guest", "passerby", "object"})
MAX_BODY = 8192
AUDIT_SECONDS = 60.0
_audit = {"at": 0.0}
_audit_lock = threading.Lock()


def _audited(user: str) -> None:
    with _audit_lock:
        if time.time() - _audit["at"] < AUDIT_SECONDS:
            return
        _audit["at"] = time.time()
    record.record("sentinel.read", record.NUXIVA, "sentinel.sentinel.memory_read", {"user": user[:40]}, "household",
                  "sentinel")


def _engine(fn):
    try:
        return fn()
    except SentinelUnavailable as exc:
        raise HTTPException(503, "sentinel_native_unavailable") from exc
    except ValueError as exc:
        raise HTTPException(400, str(exc)[:120]) from exc


async def _body(request: Request) -> dict:
    raw = await request.body()
    if len(raw) > MAX_BODY:
        raise HTTPException(413, "sentinel_body_too_large")
    try:
        data = json.loads(raw or b"{}")
    except ValueError as exc:
        raise HTTPException(400, "sentinel_body_invalid") from exc
    if not isinstance(data, dict):
        raise HTTPException(400, "sentinel_body_invalid")
    return data


def _person(slug: str) -> dict:
    if not SLUG.match(slug):
        raise HTTPException(400, "sentinel_person_invalid")
    who = memory_people.who_for(slug)
    if who is None:
        raise HTTPException(404, "sentinel_person_unknown")
    return who


@routes.get("/api/sentinel/memory/status", openapi_extra=READ)
async def memory_status(_: str = Depends(require_admin)):
    from features.sentinel import memory_vault
    policy = _engine(memory.policy)
    return JSONResponse({"policy": policy, "days": memory_vault.days()}, headers=NO_CACHE)


@routes.post("/api/sentinel/memory/search", openapi_extra=READ)
async def memory_search(request: Request, user: str = Depends(require_admin)):
    query = await _body(request)
    person = query.pop("person", None)
    if person is not None:
        if not isinstance(person, str):
            raise HTTPException(400, "sentinel_person_invalid")
        query["who"] = _person(person)
    for field in ("from_ms", "to_ms"):
        if not isinstance(query.get(field), int):
            raise HTTPException(400, "sentinel_range_invalid")
    page = _engine(lambda: memory.search(query))
    _audited(user)
    return JSONResponse(page, headers=NO_CACHE)


@routes.get("/api/sentinel/memory/person/{slug}", openapi_extra=READ)
async def memory_person(slug: str, user: str = Depends(require_admin)):
    _person(slug)
    summary = _engine(lambda: memory_people.sync(slug))
    _audited(user)
    return JSONResponse({"slug": slug, "memory": summary}, headers=NO_CACHE)


@routes.delete("/api/sentinel/memory/person/{slug}", openapi_extra=MANAGE)
async def memory_forget(slug: str, _: str = Depends(require_admin)):
    who = _person(slug)
    removed = _engine(lambda: memory.forget(who))
    record.record("sentinel.read", record.NUXIVA, "sentinel.sentinel.memory_forget", {"count": removed}, "household",
                  "sentinel")
    _engine(lambda: memory_people.sync(slug))
    return {"ok": True, "removed": removed}


@routes.put("/api/sentinel/memory/policy", openapi_extra=MANAGE)
async def memory_policy(request: Request, _: str = Depends(require_admin)):
    body = await _body(request)
    if any(k not in AUDIENCES or not isinstance(v, int) or isinstance(v, bool) for k, v in body.items()):
        raise HTTPException(400, "sentinel_retention_invalid")
    return {"ok": True, "policy": _engine(lambda: memory.configure(body))}


@routes.post("/api/sentinel/memory/pin", openapi_extra=MANAGE)
async def memory_pin(request: Request, _: str = Depends(require_admin)):
    body = await _body(request)
    day, ident, pinned = body.get("day"), body.get("id"), body.get("pinned")
    if not isinstance(day, str) or not DAY.match(day) or not isinstance(ident, str) or not ID.match(ident) \
            or not isinstance(pinned, bool):
        raise HTTPException(400, "sentinel_pin_invalid")
    return {"ok": _engine(lambda: memory.pin(day, ident, pinned))}


@routes.post("/api/sentinel/memory/sweep", openapi_extra=MANAGE)
async def memory_sweep(_: str = Depends(require_admin)):
    return _engine(memory.sweep)
