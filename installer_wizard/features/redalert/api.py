import re

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse, Response

from access import NO_CACHE, require_admin
from features.redalert.broadcast import clips
from features.redalert.service import redalert

public_routes = APIRouter()
admin_routes = APIRouter()
TOKEN_RE = re.compile(r"^[A-Za-z0-9_-]{20,64}$")


@public_routes.get("/api/redalert/audio/{token}.wav")
async def redalert_audio(token: str):
    wav = clips.get(token) if TOKEN_RE.match(token) else None
    if wav is None:
        raise HTTPException(404, "Messaggio scaduto")
    return Response(wav, media_type="audio/wav", headers=NO_CACHE)


@admin_routes.get("/api/redalert")
async def redalert_status(_: str = Depends(require_admin)):
    from features.redalert.service import enabled, excluded, repeat_after, seconds
    return JSONResponse({"enabled": enabled(), "active": redalert.active, "message": redalert.message if redalert.active else "",
                         "seconds": seconds(), "repeat": repeat_after(), "excluded": sorted(excluded())}, headers=NO_CACHE)


@admin_routes.get("/api/redalert/lights")
async def redalert_lights(_: str = Depends(require_admin)):
    from features.redalert import lights
    states = lights.snapshot()
    from features.home_assistant.home import brain
    rows = [{"id": eid, "name": str((brain.states.get(eid, {}).get("attrs") or {}).get("friendly_name") or eid)} for eid in sorted(states)]
    return JSONResponse({"lights": rows}, headers=NO_CACHE)


@admin_routes.post("/api/redalert/test")
async def redalert_test(user: str = Depends(require_admin)):
    if not redalert.trigger(f"Prova dell'allarme richiesta da {user}: nessun pericolo.", 12):
        raise HTTPException(409, "L'allarme rosso è disattivato")
    return {"ok": True}


@admin_routes.post("/api/redalert/stop")
async def redalert_stop(_: str = Depends(require_admin)):
    redalert.stop()
    return {"ok": True}
