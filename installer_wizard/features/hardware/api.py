from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request

from access import require_admin, require_display
from features.hardware.catalog import catalog
from features.hardware.expert import agent as hardware_agent
from features.hardware.service import hardware_service
from state import store
from features.hardware.localization import translate
from features.locale.api import page_language

public_routes = APIRouter()
admin_routes = APIRouter()


@public_routes.get("/api/hardware/devices")
async def public_devices(request: Request):
    require_display(request)
    return {"devices": [serialize(d, page_language(request, False)) for d in hardware_service.devices]}


@public_routes.get("/api/hardware/capabilities")
async def public_capabilities(request: Request):

    require_display(request)
    return {"capabilities": hardware_service.capabilities}


@admin_routes.get("/api/hardware/devices")
async def admin_devices(request: Request, _: str = Depends(require_admin)):
    return {"devices": [serialize(d, page_language(request, True)) for d in hardware_service.devices]}


@admin_routes.get("/api/hardware/capabilities")
async def admin_capabilities(_: str = Depends(require_admin)):
    return {"capabilities": hardware_service.capabilities}


@admin_routes.get("/api/hardware/repositories")
async def repositories_status(_: str = Depends(require_admin)):

    mgr = hardware_agent.repos
    return {
        "family": mgr.os_info.family,
        "package_manager": hardware_agent.detect_pkg_manager(),
        "components": mgr.apt_status() if hardware_agent.detect_pkg_manager() == "apt" else {},
    }


@admin_routes.get("/api/hardware/catalog")
async def driver_catalog(_: str = Depends(require_admin)):
    return {
        "recipes": [
            {"id": r.id, "name": r.name, "category": r.category, "dkms": bool(r.dkms)} for r in catalog.recipes
        ]
    }


@admin_routes.post("/api/hardware/devices/{device_id:path}/install-driver")
async def install_driver(device_id: str, approve: bool = False, _: str = Depends(require_admin)):

    dev = hardware_service.get_device(device_id)
    if not dev:
        raise HTTPException(status_code=404, detail="hardware_device_not_found")
    started = hardware_service.start_provisioning(dev, approve=approve)
    store.event("INFO", f"Avvio provisioning manuale driver per {dev.name}", "hardware")
    return {"status": "started" if started else "already_running", "device": serialize(dev)}


@admin_routes.post("/api/hardware/rescan")
async def rescan_hardware(_: str = Depends(require_admin)):
    devs = await hardware_service.refresh()
    return {"status": "ok", "count": len(devs), "devices": [serialize(d) for d in devs]}


@admin_routes.get("/api/hardware/updates")
async def managed_updates(_: str = Depends(require_admin)):
    return {"managed": hardware_service.managed.load(), "interval_seconds": 86400}


@admin_routes.post("/api/hardware/devices/{device_id:path}/update-driver")
async def update_driver(device_id: str, approve: bool = False, _: str = Depends(require_admin)):
    device = hardware_service.get_device(device_id)
    if device is None:
        raise HTTPException(404, "hardware_device_not_found")
    started = hardware_service.start_provisioning(device, approve=approve, refresh=True)
    return {"status": "started" if started else "already_running", "device": serialize(device)}


def serialize(device, language=None):
    data = device.to_dict()
    data["status_label"] = translate(data["status_label_key"], language)
    return data
