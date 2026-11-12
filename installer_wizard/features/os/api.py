from __future__ import annotations

import hmac
from access import NO_CACHE
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from features.os.taskbar_manager import taskbar_manager
from features.os.wallpaper_manager import wallpaper_manager
from features.os.window_manager import window_manager

routes = APIRouter()
public_routes = routes
admin_routes = routes


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


@routes.get("/api/os/windows")
async def get_windows() -> JSONResponse:
    return JSONResponse({"windows": window_manager.get_windows()}, headers=NO_CACHE)


@routes.post("/api/os/windows/register")
async def register_window(request: Request) -> JSONResponse:
    _verify_csrf(request)
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(400, "Invalid JSON payload")
    try:
        win = window_manager.register_window(
            window_id=body.get("id", ""),
            title=body.get("title", "Window"),
            app_id=body.get("app_id", "app"),
            width=int(body.get("width", 800)),
            height=int(body.get("height", 600)),
            x=body.get("x"),
            y=body.get("y"),
        )
        return JSONResponse({"ok": True, "window": win}, headers=NO_CACHE)
    except ValueError as exc:
        raise HTTPException(400, str(exc))


@routes.post("/api/os/windows/focus")
async def focus_window(request: Request) -> JSONResponse:
    _verify_csrf(request)
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(400, "Invalid JSON payload")
    ok = window_manager.focus_window(body.get("id", ""))
    return JSONResponse({"ok": ok}, headers=NO_CACHE)


@routes.post("/api/os/windows/state")
async def update_window_state(request: Request) -> JSONResponse:
    _verify_csrf(request)
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(400, "Invalid JSON payload")
    try:
        ok = window_manager.update_state(body.get("id", ""), body.get("state", "normal"))
        return JSONResponse({"ok": ok}, headers=NO_CACHE)
    except ValueError as exc:
        raise HTTPException(400, str(exc))


@routes.post("/api/os/windows/geometry")
async def update_window_geometry(request: Request) -> JSONResponse:
    _verify_csrf(request)
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(400, "Invalid JSON payload")
    ok = window_manager.update_geometry(
        window_id=body.get("id", ""),
        x=int(body.get("x", 0)),
        y=int(body.get("y", 0)),
        width=int(body.get("width", 800)),
        height=int(body.get("height", 600)),
    )
    return JSONResponse({"ok": ok}, headers=NO_CACHE)


@routes.delete("/api/os/windows/{window_id}")
async def close_window(window_id: str, request: Request) -> JSONResponse:
    _verify_csrf(request)
    ok = window_manager.close_window(window_id)
    return JSONResponse({"ok": ok}, headers=NO_CACHE)


@routes.get("/api/os/wallpaper")
async def get_wallpaper() -> JSONResponse:
    return JSONResponse(wallpaper_manager.get_wallpaper(), headers=NO_CACHE)


@routes.post("/api/os/wallpaper")
async def set_wallpaper(request: Request) -> JSONResponse:
    _verify_csrf(request)
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(400, "Invalid JSON payload")
    try:
        wp = wallpaper_manager.set_wallpaper(
            mode=body.get("mode", "ambient_gradient"),
            source=body.get("source", "default"),
            blur=bool(body.get("blur", False)),
        )
        return JSONResponse({"ok": True, "wallpaper": wp}, headers=NO_CACHE)
    except ValueError as exc:
        raise HTTPException(400, str(exc))


@routes.get("/api/os/taskbar")
async def get_taskbar() -> JSONResponse:
    return JSONResponse(
        {
            "pinned": taskbar_manager.get_pinned_apps(),
            "tray": taskbar_manager.get_tray_status(),
        },
        headers=NO_CACHE,
    )


@routes.post("/api/os/taskbar/pin")
async def pin_app(request: Request) -> JSONResponse:
    _verify_csrf(request)
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(400, "Invalid JSON payload")
    ok = taskbar_manager.pin_app(
        app_id=body.get("app_id", ""),
        title_key=body.get("title_key", ""),
        icon=body.get("icon", "app"),
    )
    return JSONResponse({"ok": ok}, headers=NO_CACHE)


@routes.post("/api/os/taskbar/unpin")
async def unpin_app(request: Request) -> JSONResponse:
    _verify_csrf(request)
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(400, "Invalid JSON payload")
    ok = taskbar_manager.unpin_app(body.get("app_id", ""))
    return JSONResponse({"ok": ok}, headers=NO_CACHE)
