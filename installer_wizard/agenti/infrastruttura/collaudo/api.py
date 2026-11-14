import asyncio
import json
import time
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, ConfigDict, Field

import native_core
from access import NO_CACHE
from agenti.collaudo import emit, hub, paths, smoke, tokens

admin_routes = APIRouter(prefix="/api/collaudo", tags=["Collaudo"])
LOOPBACK = {"127.0.0.1", "::1"}
POLL = 0.25
KEEPALIVE = 15.0
LANG_DIR = Path(__file__).resolve().parent / "language"
LEVELS = "^(trace|debug|info|warn|error)$"
DOMAINS = "^(sentinel|ear|vision|supervisor|worker|mcp|error|resource|probe|system)$"
TOKEN_RE = "^[a-z0-9_.:-]{1,48}$"


def peer(request: Request) -> str:
    return request.client.host if request.client else ""


def guard(request: Request) -> None:
    if not tokens.armed():
        raise HTTPException(404, "collaudo.disarmed")
    if peer(request) not in LOOPBACK:
        raise HTTPException(403, "collaudo.local_only")
    if tokens.throttled():
        raise HTTPException(429, "collaudo.throttled")
    header = request.headers.get("authorization", "")
    presented = header[7:].strip() if header[:7].lower() == "bearer " else ""
    if not tokens.verify(presented):
        tokens.failed()
        raise HTTPException(401, "collaudo.unauthorized")
    if request.method in ("POST", "PUT", "DELETE") and request.headers.get("X-Nuxiva-Request") != "1":
        raise HTTPException(403, "collaudo.invalid_request")


class Mode(BaseModel):
    model_config = ConfigDict(extra="forbid")
    enabled: bool


class Smoke(BaseModel):
    model_config = ConfigDict(extra="forbid")
    only: list[str] = Field(default_factory=list, max_length=32)


class Scenario(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(pattern=TOKEN_RE)
    seconds: float = Field(10.0, ge=3.0, le=120.0)


class Mark(BaseModel):
    model_config = ConfigDict(extra="forbid")
    label: str = Field(pattern=TOKEN_RE)


def hints(lang: str) -> dict:
    code = lang if lang in ("it", "en", "fr", "es") else "en"
    try:
        return json.loads((LANG_DIR / f"{code}.json").read_text(encoding="utf-8")).get("hints", {})
    except (OSError, ValueError):
        return {}


def query_args(since_seq: int, domain: str | None, min_level: str | None, corr: str | None, kind_prefix: str | None,
               from_ms: int | None, limit: int) -> dict:
    args = {"since_seq": since_seq, "domain": domain, "min_level": min_level, "corr": corr, "kind_prefix": kind_prefix,
            "from_ms": from_ms, "limit": limit}
    return {k: v for k, v in args.items() if v is not None}


@admin_routes.get("/status", dependencies=[Depends(guard)])
async def status() -> JSONResponse:
    h = hub.get()
    last = await asyncio.to_thread(hub.query, {"since_seq": 0, "limit": 1})
    return JSONResponse({"armed": True, "native": hub.native(), "collaudo": h.collaudo(), "stats": json.loads(h.stats()),
                         "first_seq": last[0]["seq"] if last else None, "now_ms": int(time.time() * 1000)}, headers=NO_CACHE)


@admin_routes.get("/events", dependencies=[Depends(guard)])
async def events(since_seq: int = Query(0, ge=0), domain: str | None = Query(None, pattern=DOMAINS),
                 min_level: str | None = Query(None, pattern=LEVELS), corr: str | None = Query(None, pattern="^[0-9a-f]{8,32}$"),
                 kind_prefix: str | None = Query(None, pattern=TOKEN_RE), from_ms: int | None = Query(None, ge=0),
                 limit: int = Query(500, ge=1, le=5000)) -> JSONResponse:
    rows = await asyncio.to_thread(hub.query, query_args(since_seq, domain, min_level, corr, kind_prefix, from_ms, limit))
    return JSONResponse({"events": rows, "last_seq": rows[-1]["seq"] if rows else since_seq}, headers=NO_CACHE)


@admin_routes.get("/stream", dependencies=[Depends(guard)])
async def stream(request: Request, since_seq: int = Query(-1, ge=-1), domain: str | None = Query(None, pattern=DOMAINS),
                 min_level: str | None = Query(None, pattern=LEVELS)) -> StreamingResponse:
    resume = request.headers.get("last-event-id", "")
    cursor = since_seq if since_seq >= 0 else int(resume) if resume.isdigit() else None

    async def generator():
        position = cursor
        if position is None:
            tail = await asyncio.to_thread(hub.query, {"since_seq": 0, "limit": 5000})
            position = tail[-1]["seq"] if tail else 0
        idle = 0.0
        while not await request.is_disconnected():
            rows = await asyncio.to_thread(hub.query, query_args(position, domain, min_level, None, None, None, 500))
            for row in rows:
                position = row["seq"]
                yield f"id: {position}\ndata: {json.dumps(row, ensure_ascii=False)}\n\n"
            if not rows:
                idle += POLL
                if idle >= KEEPALIVE:
                    idle = 0.0
                    yield ": keepalive\n\n"
            else:
                idle = 0.0
            await asyncio.sleep(POLL)

    return StreamingResponse(generator(), media_type="text/event-stream", headers={**NO_CACHE, "X-Accel-Buffering": "no"})


@admin_routes.post("/mode", dependencies=[Depends(guard)])
async def mode(body: Mode) -> JSONResponse:
    hub.set_mode(body.enabled)
    emit.emit("system", "info", "mode_changed", src="collaudo", enabled=body.enabled)
    return JSONResponse({"collaudo": body.enabled}, headers=NO_CACHE)


@admin_routes.post("/mark", dependencies=[Depends(guard)])
async def mark(body: Mark) -> JSONResponse:
    corr = emit.new_corr()
    emit.emit("system", "info", "mark", src="operator", corr=corr, label=body.label)
    return JSONResponse({"corr": corr}, headers=NO_CACHE)


@admin_routes.post("/smoke", dependencies=[Depends(guard)])
async def run_smoke(body: Smoke, lang: str = Query("en", pattern="^[a-z]{2}$")) -> JSONResponse:
    if any(name not in smoke.ACTIVE and name != "collaudo_chain" for name in body.only):
        raise HTTPException(422, "collaudo.smoke.unknown_probe")
    result = await smoke.run(body.only or None)
    result["hints"] = hints(lang)
    return JSONResponse(result, headers=NO_CACHE)


@admin_routes.post("/scenario", dependencies=[Depends(guard)])
async def run_scenario(body: Scenario) -> JSONResponse:
    try:
        return JSONResponse(await smoke.scenario(body.name, body.seconds), headers=NO_CACHE)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


@admin_routes.get("/report", dependencies=[Depends(guard)])
async def report(minutes: int = Query(15, ge=1, le=1440), lang: str = Query("en", pattern="^[a-z]{2}$")) -> JSONResponse:
    current = await asyncio.to_thread(hub.report, {"from_ms": int((time.time() - minutes * 60) * 1000)})
    regressions: list = []
    if paths.BASELINE.exists():
        comparer = native_core.symbol("collaudo_compare")
        if comparer is not None:
            before = paths.BASELINE.read_text(encoding="utf-8")
            regressions = json.loads(comparer(before, json.dumps(current)))
    return JSONResponse({"report": current, "regressions": regressions, "hints": hints(lang)}, headers=NO_CACHE)


@admin_routes.post("/baseline", dependencies=[Depends(guard)])
async def baseline(minutes: int = Query(15, ge=1, le=1440)) -> JSONResponse:
    current = await asyncio.to_thread(hub.report, {"from_ms": int((time.time() - minutes * 60) * 1000)})
    paths.ROOT.mkdir(parents=True, exist_ok=True, mode=0o700)
    paths.BASELINE.write_text(json.dumps(current), encoding="utf-8")
    paths.BASELINE.chmod(0o600)
    return JSONResponse({"saved": True, "events": current["events"]}, headers=NO_CACHE)


@admin_routes.get("/verify", dependencies=[Depends(guard)])
async def verify() -> JSONResponse:
    return JSONResponse(json.loads(await asyncio.to_thread(hub.get().verify)), headers=NO_CACHE)
