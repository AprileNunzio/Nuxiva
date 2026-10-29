from __future__ import annotations

import asyncio
from fastapi import APIRouter, Depends, HTTPException, Request

from access import require_admin, require_display
from features.hardware.expert import agent as hardware_agent
from features.hardware.service import hardware_service
from state import store

public_routes = APIRouter()
admin_routes = APIRouter()


@public_routes.get("/api/hardware/devices")
async def public_devices(request: Request):
    require_display(request)
    return {"devices": [d.to_dict() for d in hardware_service.devices]}


@admin_routes.get("/api/hardware/devices")
async def admin_devices(_: str = Depends(require_admin)):
    return {"devices": [d.to_dict() for d in hardware_service.devices]}


@admin_routes.post("/api/hardware/devices/{device_id:path}/install-driver")
async def install_driver(device_id: str, _: str = Depends(require_admin)):
    dev = hardware_service.get_device(device_id)
    if not dev:
        raise HTTPException(status_code=404, detail="Dispositivo non trovato")
    asyncio.create_task(hardware_agent.provision(dev))
    store.event("INFO", f"Avvio provisioning manuale driver per {dev.name}", "hardware")
    return {"status": "started", "device": dev.to_dict()}


@admin_routes.post("/api/hardware/rescan")
async def rescan_hardware(_: str = Depends(require_admin)):
    devs = await hardware_service.refresh()
    return {"status": "ok", "count": len(devs), "devices": [d.to_dict() for d in devs]}
