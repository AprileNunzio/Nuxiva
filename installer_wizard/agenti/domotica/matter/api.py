from access import NO_CACHE, require_admin
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from agenti.matter.coordinator import MatterCoordinator

admin_routes = APIRouter(prefix="/api/matter", tags=["matter"])
MANAGE = {"x-nuxiva-capabilities": ["matter.manage"]}

@admin_routes.get("/status", dependencies=[Depends(require_admin)], openapi_extra=MANAGE)
async def matter_status():
    coordinator = MatterCoordinator.instance()
    return JSONResponse(coordinator.get_status(), headers=NO_CACHE)

@admin_routes.get("/nodes", dependencies=[Depends(require_admin)], openapi_extra=MANAGE)
async def matter_nodes():
    coordinator = MatterCoordinator.instance()
    return JSONResponse({"nodes": coordinator.list_nodes()}, headers=NO_CACHE)

@admin_routes.get("/discover", dependencies=[Depends(require_admin)], openapi_extra=MANAGE)
async def matter_discover(timeout: float = 1.5):
    coordinator = MatterCoordinator.instance()
    devices = coordinator.discover_network_devices(timeout=timeout)
    return JSONResponse({"discovered": devices}, headers=NO_CACHE)

@admin_routes.post("/auto_enroll", dependencies=[Depends(require_admin)], openapi_extra=MANAGE)
async def matter_auto_enroll(request: Request):
    try:
        data = await request.json()
    except Exception as exc:
        raise HTTPException(400, "matter.invalid_payload") from exc
    coordinator = MatterCoordinator.instance()
    res = coordinator.auto_enroll_device(data)
    return JSONResponse(res, headers=NO_CACHE)

@admin_routes.post("/commission", dependencies=[Depends(require_admin)], openapi_extra=MANAGE)
async def matter_commission(request: Request):
    try:
        data = await request.json()
    except Exception as exc:
        raise HTTPException(400, "matter.invalid_payload") from exc
    code = str(data.get("pairing_code") or "")
    if not code:
        raise HTTPException(400, "matter.missing_pairing_code")
    name = str(data.get("name")) if data.get("name") else None
    dev_type = int(data["device_type"]) if data.get("device_type") else None

    coordinator = MatterCoordinator.instance()
    res = coordinator.commission_node(code, name=name, device_type=dev_type)
    return JSONResponse(res, headers=NO_CACHE)

@admin_routes.post("/clusters/invoke", dependencies=[Depends(require_admin)], openapi_extra=MANAGE)
async def matter_invoke(request: Request):
    try:
        data = await request.json()
    except Exception as exc:
        raise HTTPException(400, "matter.invalid_payload") from exc
    try:
        node_id = int(data["node_id"])
        ep_id = int(data["endpoint_id"])
        cl_id = int(data["cluster_id"])
        cmd_id = int(data["command_id"])
        payload = data.get("payload")
    except KeyError as exc:
        raise HTTPException(400, f"matter.missing_{exc}") from exc

    coordinator = MatterCoordinator.instance()
    res = coordinator.invoke_node_command(node_id, ep_id, cl_id, cmd_id, payload)
    if res.get("status") == "error":
        raise HTTPException(400, res.get("message"))
    return JSONResponse(res, headers=NO_CACHE)

@admin_routes.get("/bridge/endpoints", dependencies=[Depends(require_admin)], openapi_extra=MANAGE)
async def matter_bridge_endpoints():
    coordinator = MatterCoordinator.instance()
    return JSONResponse({"endpoints": coordinator.list_bridge_endpoints()}, headers=NO_CACHE)

@admin_routes.post("/bridge/sync", dependencies=[Depends(require_admin)], openapi_extra=MANAGE)
async def matter_bridge_sync():
    coordinator = MatterCoordinator.instance()
    res = coordinator.sync_system_devices()
    return JSONResponse(res, headers=NO_CACHE)

@admin_routes.post("/bridge/state", dependencies=[Depends(require_admin)], openapi_extra=MANAGE)
async def matter_bridge_state(request: Request):
    try:
        data = await request.json()
    except Exception as exc:
        raise HTTPException(400, "matter.invalid_payload") from exc
    try:
        entity_id = str(data["entity_id"])
        cl_id = int(data["cluster_id"])
        attr_id = int(data["attr_id"])
        val = data["value"]
    except KeyError as exc:
        raise HTTPException(400, f"matter.missing_{exc}") from exc

    coordinator = MatterCoordinator.instance()
    ok = coordinator.update_bridge_state(entity_id, cl_id, attr_id, val)
    if not ok:
        raise HTTPException(404, "matter.entity_not_found")
    return JSONResponse({"ok": True, "entity_id": entity_id}, headers=NO_CACHE)
