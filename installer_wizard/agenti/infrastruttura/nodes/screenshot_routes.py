from access import require_internal
from fastapi import APIRouter, Request

from agenti.nodes import screenshot_service

public_routes = APIRouter()


@public_routes.post("/api/display/screenshot")
async def display_screenshot(request: Request):
    require_internal(request)
    return await screenshot_service.take()
