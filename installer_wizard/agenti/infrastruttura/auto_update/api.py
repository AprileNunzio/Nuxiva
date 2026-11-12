from __future__ import annotations

import hmac

from access import NO_CACHE, is_local, require_admin
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from agenti.auto_update.self_healing import self_healer
from agenti.auto_update.service import update_service
from state import store

public_routes = APIRouter()
admin_routes = APIRouter()


def _verify_origin_and_csrf(request: Request) -> None:
    if request.method in ("POST", "PUT", "DELETE"):
        token = request.headers.get("X-Nuxiva-Request")
        if not token or not hmac.compare_digest(str(token), "1"):
            raise HTTPException(403, "Richiesta non valida")
        origin = request.headers.get("origin")
        if origin:
            host = request.headers.get("host", "")
            if origin.split("://", 1)[-1].rstrip("/") != host:
                raise HTTPException(403, "Origine non autorizzata")


@public_routes.get("/api/system/update/status")
@admin_routes.get("/api/system/update/status")
async def get_system_update_status(request: Request) -> JSONResponse:
    info = store.update
    import updater
    local = await updater.current_rev()
    return JSONResponse(
        {
            "local_rev": local,
            "remote_rev": info.get("remote_rev"),
            "target_rev": info.get("target_rev"),
            "available": bool(info.get("available")),
            "changelog": list(info.get("changelog") or [])[:15],
            "last_check": info.get("last_check"),
            "last_result": info.get("last_result"),
            "check_error": info.get("check_error"),
        },
        headers=NO_CACHE,
    )


@public_routes.post("/api/system/update/check")
@admin_routes.post("/api/system/update/check")
async def check_system_updates(
    request: Request, _: None = Depends(_verify_origin_and_csrf)
) -> JSONResponse:
    result = await update_service.check_updates(fresh=True)
    return JSONResponse(result, headers=NO_CACHE)


@admin_routes.post("/api/system/update/apply")
async def apply_system_update(
    request: Request,
    _: None = Depends(require_admin),
    __: None = Depends(_verify_origin_and_csrf),
) -> JSONResponse:
    result = await update_service.trigger_update(force=True)
    return JSONResponse(result, headers=NO_CACHE)


@public_routes.post("/api/system/update/heal")
@admin_routes.post("/api/system/update/heal")
async def trigger_self_healing(
    request: Request, _: None = Depends(_verify_origin_and_csrf)
) -> JSONResponse:
    if not is_local(request):
        raise HTTPException(403, "Operazione permessa solo localmente")
    results = self_healer.run_all()
    return JSONResponse({"ok": True, "details": results}, headers=NO_CACHE)
