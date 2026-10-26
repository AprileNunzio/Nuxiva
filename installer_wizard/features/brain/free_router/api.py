import time

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request

from access import require_admin
from features.brain.free_router import capability_matrix, catalog_poller, rate_limiter, settings, telemetry_emitter
from state import store
from tasks import background

admin_routes = APIRouter()


async def _refresh_catalog() -> None:
    try:
        await catalog_poller.refresh()
    except (httpx.HTTPError, OSError, ValueError) as exc:
        store.event("WARN", f"free_router.catalog_unavailable: {type(exc).__name__}", "brain")


@admin_routes.get("/api/brains/free-matrix")
async def overview(_: str = Depends(require_admin)):
    configured = settings.load()
    models = catalog_poller.cached()
    if not catalog_poller.updated_at() or time.time() - catalog_poller.updated_at() >= catalog_poller.REFRESH_SECONDS:
        background(_refresh_catalog())
    metrics = rate_limiter.rate_limiter.metrics()
    return {"enabled": configured["enabled"], "pools": configured["pools"], "updated_at": catalog_poller.updated_at(),
            "live": telemetry_emitter.current(),
            "models": [{**model, "pools": [pool for pool in capability_matrix.POOLS
                                            if capability_matrix.supports(model, pool, metrics.get(model["id"]))],
                        "rate": metrics.get(model["id"], {})} for model in models]}


@admin_routes.post("/api/brains/free-matrix/refresh")
async def refresh(_: str = Depends(require_admin)):
    try:
        models = await catalog_poller.refresh(force=True)
    except (httpx.HTTPError, OSError, ValueError) as exc:
        raise HTTPException(502, "free_router.catalog_unavailable") from exc
    store.event("INFO", f"free_router.catalog_refreshed: {len(models)}", "brain")
    return {"count": len(models), "updated_at": catalog_poller.updated_at()}


@admin_routes.put("/api/brains/free-matrix")
async def configure(request: Request, user: str = Depends(require_admin)):
    body = await request.json()
    if not isinstance(body, dict):
        raise HTTPException(400, "free_router.settings_invalid")
    try:
        saved = settings.save(body.get("enabled"), body.get("pools"))
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    store.event("INFO", f"free_router.settings_updated by {user}", "brain")
    return saved
