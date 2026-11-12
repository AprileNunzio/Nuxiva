from fastapi import APIRouter, Depends, Query

from access import require_admin
from features.research import service

public_routes = APIRouter()
admin_routes = APIRouter()


@admin_routes.get("/api/research")
async def search(q: str = Query(..., min_length=2, max_length=200), days: int = Query(0, ge=0, le=366), limit: int = Query(5, ge=1, le=8),
                 _: str = Depends(require_admin)):
    return await service.research(q, days, limit)
