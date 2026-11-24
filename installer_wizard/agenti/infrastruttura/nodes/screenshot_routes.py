from access import require_internal
from fastapi import APIRouter, HTTPException, Request

from agenti.nodes import screenshot_bridge

public_routes = APIRouter()


@public_routes.post("/api/display/screenshot")
async def display_screenshot(request: Request):
    require_internal(request)
    try:
        screenshot_bridge.request()
    except screenshot_bridge.BridgeUnavailable as exc:
        raise HTTPException(503, "screenshot_service_unavailable") from exc
    return {"requested": True}
