from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse, Response

from access import NO_CACHE, require_admin
from features.authz.access_control import require_permission
from features.system_logs import service

admin_routes = APIRouter(prefix="/api/v5/logs", tags=["System Logs"], dependencies=[Depends(require_admin)])


def public_catalog(payload: dict) -> dict:
    return {**payload, "sources": [{key: service.redact(value) if isinstance(value, str) and key != "id" else value for key, value in source.items() if not key.startswith("_")} for source in payload["sources"]]}


@admin_routes.get("/sources", openapi_extra={"x-nuxiva-capabilities": ["logs.read"]})
async def sources(node_id: str = Query("local", pattern=r"^[A-Za-z0-9._:@-]{1,128}$"), user: str = Depends(require_admin)):
    require_permission(user, "logs.read", node_id)
    try:
        return JSONResponse(public_catalog(await service.discover(node_id)), headers=NO_CACHE)
    except (OSError, RuntimeError) as exc:
        raise HTTPException(503, "log_discovery_unavailable") from exc


@admin_routes.get("/entries", openapi_extra={"x-nuxiva-capabilities": ["logs.read"]})
@admin_routes.get("/export", openapi_extra={"x-nuxiva-capabilities": ["logs.read"]})
async def logs(source: str = Query("events", max_length=200), node_id: str = Query("local", pattern=r"^[A-Za-z0-9._:@-]{1,128}$"),
               minutes: int = Query(60, ge=1, le=43200), limit: int = Query(300, ge=1, le=service.MAX_LINES),
               severity: Literal["all", "error", "warning", "info", "debug"] = "all", query: str = Query("", max_length=200),
               format: Literal["view", "txt", "json", "csv", "report"] = "view", user: str = Depends(require_admin)):
    require_permission(user, "logs.export" if format != "view" else "logs.read", node_id)
    try:
        payload = await service.entries(source, node_id, minutes, limit, severity, query)
    except KeyError as exc:
        raise HTTPException(404, str(exc)) from exc
    except (OSError, RuntimeError) as exc:
        raise HTTPException(503, "log_source_unavailable") from exc
    if format == "view":
        return JSONResponse(payload, headers=NO_CACHE)
    if format == "report":
        payload = await service.diagnostics(payload)
    content, media_type = service.export(payload, format)
    extension = "json" if format == "report" else format
    return Response(content, media_type=media_type, headers={**NO_CACHE, "Content-Disposition": f'attachment; filename="nuxiva-logs.{extension}"'})
