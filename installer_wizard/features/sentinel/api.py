import json
import re
import threading
import time
from collections import Counter

from access import NO_CACHE, require_admin
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse

from features.sentinel import narrate, record, vault
from features.sentinel.collectors import automations
from features.sentinel.journal import SentinelUnavailable, day_bounds, journal
from features.sentinel.journey_detail import routes as journey_routes
from features.sentinel.memory_api import routes as memory_routes

admin_routes = APIRouter()
admin_routes.include_router(memory_routes)
admin_routes.include_router(journey_routes)
READ = {"x-nuxiva-capabilities": ["sentinel.read"]}
MANAGE = {"x-nuxiva-capabilities": ["sentinel.manage"]}
GROUPS = frozenset({"presence", "appearance", "guests", "guest_appearance", "voice", "access", "denied", "automations",
                    "nuxiva", "display", "system", "audit"})
SLUG = re.compile(r"^[a-z0-9_.-]{1,64}$")
ID = re.compile(r"^[0-9a-f]{16,32}$")
DAY = re.compile(r"^\d{4}-\d{2}-\d{2}$")
LANGS = frozenset(narrate.LANGS)
AUDIT_SECONDS = 60.0
_audit = {"at": 0.0}
_audit_lock = threading.Lock()


def _listen() -> None:
    from features.automations.bus import bus
    bus.listen(automations.on_event)


_listen()


def _lang(raw: str | None) -> str:
    return raw if raw in LANGS else "it"


def _audited(user: str) -> None:
    with _audit_lock:
        if time.time() - _audit["at"] < AUDIT_SECONDS:
            return
        _audit["at"] = time.time()
    record.record("sentinel.read", record.NUXIVA, "sentinel.sentinel.read", {"user": user[:40]}, "household", "sentinel")


def _engine_errors(fn):
    try:
        return fn()
    except SentinelUnavailable as exc:
        raise HTTPException(503, "sentinel_native_unavailable") from exc
    except ValueError as exc:
        raise HTTPException(400, str(exc)[:120]) from exc


def _query(from_ms: int, to_ms: int, groups: str, person: str | None, limit: int, before_at: int | None,
           before_id: str | None) -> dict:
    wanted = [g for g in groups.split(",") if g] if groups else []
    if any(g not in GROUPS for g in wanted) or len(wanted) > 12:
        raise HTTPException(400, "sentinel_groups_invalid")
    if person is not None and not SLUG.match(person):
        raise HTTPException(400, "sentinel_person_invalid")
    if (before_at is None) != (before_id is None) or (before_id is not None and not ID.match(before_id)):
        raise HTTPException(400, "sentinel_cursor_invalid")
    query = {"from_ms": from_ms, "to_ms": to_ms, "groups": wanted, "limit": limit,
             "subject": f"person:{record.pseudonym(person)}" if person else None}
    if before_at is not None:
        query["before"] = [before_at, before_id]
    return query


@admin_routes.get("/api/sentinel/status", openapi_extra=READ)
async def sentinel_status(_: str = Depends(require_admin)):
    try:
        journal.ready()
        native = True
    except SentinelUnavailable:
        native = False
    import native_module
    return JSONResponse({"enabled": record.enabled(), "native": native, "build": native_module.build_status(),
                         "days": vault.days() if native else [],
                         "retention": json.loads(journal.engine.retention()) if native else None}, headers=NO_CACHE)


@admin_routes.get("/api/sentinel/events", openapi_extra=READ)
async def sentinel_events(from_ms: int, to_ms: int, groups: str = "", person: str | None = None, limit: int = 50,
                          before_at: int | None = None, before_id: str | None = None, lang: str | None = None,
                          user: str = Depends(require_admin)):
    query = _query(from_ms, to_ms, groups, person, limit, before_at, before_id)
    page = _engine_errors(lambda: journal.query(query))
    language = _lang(lang)
    for event in page["events"]:
        event["text"] = narrate.text(event, language)
        event["group"] = event["kind"].split(".", 1)[0]
        if event["kind"] == "self.chat_request":
            event["journey_id"] = event["narrative"]["params"].get("journey") or None
    _audited(user)
    return JSONResponse(page, headers=NO_CACHE)


@admin_routes.get("/api/sentinel/summary", openapi_extra=READ)
async def sentinel_summary(day: str, user: str = Depends(require_admin)):
    if not DAY.match(day):
        raise HTTPException(400, "sentinel_day_invalid")
    start, end = day_bounds(day)
    events, before = [], None
    while True:
        query = {"from_ms": start, "to_ms": end, "groups": [], "limit": 200, "subject": None}
        if before:
            query["before"] = before
        page = _engine_errors(lambda q=query: journal.query(q))
        events.extend(page["events"])
        before = page.get("next")
        if not before or len(events) >= 10_000:
            break
    kinds = Counter(e["kind"] for e in events)
    guests = {e["subject"].get("id") for e in events if e["kind"] == "guest.arrived"}
    _audited(user)
    return JSONResponse({"day": day, "total": len(events), "kinds": dict(kinds), "guests": len(guests),
                         "integrity": _engine_errors(lambda: journal.integrity(day))}, headers=NO_CACHE)


@admin_routes.delete("/api/sentinel/events", openapi_extra=MANAGE)
async def sentinel_delete(from_ms: int, to_ms: int, person: str | None = None, _: str = Depends(require_admin)):
    if person is not None and not SLUG.match(person):
        raise HTTPException(400, "sentinel_person_invalid")
    subject = f"person:{record.pseudonym(person)}" if person else None
    removed = _engine_errors(lambda: journal.delete(from_ms, to_ms, subject))
    return {"ok": True, "removed": removed}


@admin_routes.put("/api/sentinel/retention", openapi_extra=MANAGE)
async def sentinel_retention(request: Request, _: str = Depends(require_admin)):
    body = await request.json()
    if not isinstance(body, dict) or any(k not in GROUPS or not isinstance(v, int) for k, v in body.items()):
        raise HTTPException(400, "sentinel_retention_invalid")
    _engine_errors(lambda: journal.configure(body))
    vault.save_retention(body)
    return {"ok": True, "retention": json.loads(journal.engine.retention())}


@admin_routes.post("/api/sentinel/sweep", openapi_extra=MANAGE)
async def sentinel_sweep(_: str = Depends(require_admin)):
    return _engine_errors(journal.sweep)
