from fastapi import APIRouter, Depends

from access import require_admin

admin_routes = APIRouter()


@admin_routes.get("/api/display/explain")
async def display_explain(_: str = Depends(require_admin)):
    from features.desktop.planner_bridge import bridge
    return bridge.explain()
