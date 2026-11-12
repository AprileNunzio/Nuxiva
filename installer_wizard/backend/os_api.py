from __future__ import annotations

import hmac
import time
from access import NO_CACHE, require_admin
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from os_memory import memory_manager
from os_notification import notification_manager
from os_process import process_manager
from agenti.auto_update.boot_updater import boot_updater

public_routes = APIRouter()
admin_routes = APIRouter()

START_TIME = time.time()


def _verify_csrf(request: Request) -> None:
    if request.method in ("POST", "PUT", "DELETE"):
        token = request.headers.get("X-Nuxiva-Request")
        if not token or not hmac.compare_digest(str(token), "1"):
            raise HTTPException(403, "Richiesta non valida")
        origin = request.headers.get("origin")
        if origin:
            host = request.headers.get("host", "")
            if origin.split("://", 1)[-1].rstrip("/") != host:
                raise HTTPException(403, "Origine non autorizzata")


@public_routes.get("/api/os/status")
@admin_routes.get("/api/os/status")
async def get_os_status() -> JSONResponse:
    mem = memory_manager.sample()
    uptime_s = round(time.time() - START_TIME, 1)
    return JSONResponse(
        {
            "uptime_seconds": uptime_s,
            "memory_state": mem.get("state", "normal"),
            "memory_percent": mem.get("percent", 0.0),
            "notifications_count": notification_manager.count(),
            "throttled": memory_manager.is_throttled(),
        },
        headers=NO_CACHE,
    )


@public_routes.get("/api/os/memory")
@admin_routes.get("/api/os/memory")
async def get_os_memory() -> JSONResponse:
    data = memory_manager.sample()
    return JSONResponse(data, headers=NO_CACHE)


@public_routes.get("/api/os/processes")
@admin_routes.get("/api/os/processes")
async def get_os_processes() -> JSONResponse:
    procs = process_manager.get_all()
    return JSONResponse({"processes": procs}, headers=NO_CACHE)


@public_routes.get("/api/os/notifications")
@admin_routes.get("/api/os/notifications")
async def get_os_notifications() -> JSONResponse:
    items = notification_manager.get_all()
    return JSONResponse({"notifications": items}, headers=NO_CACHE)


@admin_routes.post("/api/os/notifications/clear")
async def clear_os_notifications(
    request: Request,
    user: str = Depends(require_admin),
    _: None = Depends(_verify_csrf),
) -> JSONResponse:
    notification_manager.clear()
    return JSONResponse({"ok": True}, headers=NO_CACHE)


@admin_routes.post("/api/os/notifications/test")
async def send_test_notification(
    request: Request,
    user: str = Depends(require_admin),
    _: None = Depends(_verify_csrf),
) -> JSONResponse:
    item = notification_manager.notify(
        level="INFO",
        code="test_alert",
        label_key="os_system_event",
        message="Notifica di test generata con successo",
        details={"sender": user},
        force=True,
    )
    return JSONResponse({"ok": True, "notification": item.to_dict() if item else None}, headers=NO_CACHE)


@admin_routes.post("/api/os/boot_check")
async def trigger_boot_check(
    request: Request,
    user: str = Depends(require_admin),
    _: None = Depends(_verify_csrf),
) -> JSONResponse:
    res = await boot_updater.execute_boot_check()
    return JSONResponse(res, headers=NO_CACHE)
