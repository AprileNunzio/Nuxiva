from __future__ import annotations

from access import NO_CACHE, require_admin, require_display
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse

from resource_manager import DEVICE_RE, clean_report, resource_manager

public_routes = APIRouter()
admin_routes = APIRouter()
MAX_BODY = 16384


@public_routes.post("/api/resources/report")
async def report(request: Request) -> JSONResponse:
    require_display(request, "Solo dal display")
    raw = await request.body()
    if len(raw) > MAX_BODY:
        raise HTTPException(413, "Rapporto troppo grande")
    try:
        body = await request.json()
    except ValueError:
        raise HTTPException(400, "Rapporto non valido") from None
    clean = clean_report(body)
    if clean is None:
        raise HTTPException(400, "Rapporto non valido")
    return JSONResponse(resource_manager.report(clean), headers=NO_CACHE)


@public_routes.get("/api/resources/directive")
async def directive(request: Request, device: str = "") -> JSONResponse:
    require_display(request, "Solo dal display")
    if not DEVICE_RE.fullmatch(device):
        raise HTTPException(400, "Dispositivo non valido")
    return JSONResponse(resource_manager.directive_for(device), headers=NO_CACHE)


@admin_routes.get("/api/resources/state")
async def state(_: str = Depends(require_admin)) -> JSONResponse:
    return JSONResponse(resource_manager.snapshot(), headers=NO_CACHE)
