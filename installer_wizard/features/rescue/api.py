from access import NO_CACHE, require_admin
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse

from features.rescue.coordinator import coordinator

admin_routes = APIRouter(prefix="/api/rescue", tags=["rescue"])
MANAGE = {"x-nuxiva-capabilities": ["rescue.manage", "sentinel.manage"]}


@admin_routes.get("/status", dependencies=[Depends(require_admin)], openapi_extra=MANAGE)
async def rescue_status():
    return JSONResponse(coordinator.status(), headers=NO_CACHE)


@admin_routes.post("/observe", dependencies=[Depends(require_admin)], openapi_extra=MANAGE)
async def rescue_observe(request: Request):
    try:
        data = await request.json()
    except Exception as exc:
        raise HTTPException(400, "rescue.invalid_payload") from exc
    kind = str(data.get("kind") or "")
    source = str(data.get("source") or "")
    if not kind or not source:
        raise HTTPException(400, "rescue.missing_fields")
    try:
        prob = float(data.get("probability", 0.9))
        conf = float(data.get("confidence", 0.8))
        at = float(data["at"]) if "at" in data else None
        now = float(data["now"]) if "now" in data else None
        room = str(data["room"]) if data.get("room") else None
        step = coordinator.observe(kind, prob, conf, source, at=at, now=now, room=room)
        return JSONResponse({"ok": True, "step": step}, headers=NO_CACHE)
    except Exception as exc:
        raise HTTPException(400, str(exc)[:120]) from exc


@admin_routes.post("/respond", dependencies=[Depends(require_admin)], openapi_extra=MANAGE)
async def rescue_respond(request: Request):
    try:
        data = await request.json()
    except Exception as exc:
        raise HTTPException(400, "rescue.invalid_payload") from exc
    action = str(data.get("action") or "").lower()
    now = float(data["now"]) if "now" in data else None
    if action == "person_ok":
        step = coordinator.person_ok(now=now)
    elif action == "need_help":
        step = coordinator.need_help(now=now)
    elif action == "acknowledge":
        tier = int(data.get("tier", 0))
        step = coordinator.acknowledge(tier, now=now)
    elif action == "dismiss":
        step = coordinator.dismiss(now=now)
    else:
        raise HTTPException(400, "rescue.unknown_action")
    return JSONResponse({"ok": True, "step": step}, headers=NO_CACHE)


@admin_routes.get("/policy", dependencies=[Depends(require_admin)], openapi_extra=MANAGE)
async def rescue_policy_get():
    return JSONResponse(coordinator.rescue.policy(), headers=NO_CACHE)


@admin_routes.post("/policy", dependencies=[Depends(require_admin)], openapi_extra=MANAGE)
async def rescue_policy_set(request: Request):
    try:
        data = await request.json()
    except Exception as exc:
        raise HTTPException(400, "rescue.invalid_payload") from exc
    try:
        policy = coordinator.set_policy(data)
        return JSONResponse({"ok": True, "policy": policy}, headers=NO_CACHE)
    except Exception as exc:
        raise HTTPException(400, str(exc)[:120]) from exc
