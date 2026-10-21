import json

from fastapi import APIRouter, HTTPException, Request

from access import require_display
from features.models3d import library, studio

public_routes = APIRouter()
admin_routes = APIRouter()
MAX_BODY = 8192


async def _body(request: Request) -> dict:
    raw = await request.body()
    if len(raw) > MAX_BODY:
        raise HTTPException(413, "Richiesta troppo grande")
    try:
        body = json.loads(raw or b"{}")
    except ValueError:
        raise HTTPException(400, "JSON non valido")
    if not isinstance(body, dict):
        raise HTTPException(400, "Atteso un oggetto JSON")
    return body


def _meta(mid: str) -> dict:
    try:
        return library.get(mid)
    except KeyError:
        raise HTTPException(404, "Modello sconosciuto")


@public_routes.get("/api/models3d/{mid}/studio")
async def studio_state(mid: str, request: Request):
    require_display(request, "Solo dal display")
    return studio.state(_meta(mid))


@public_routes.post("/api/models3d/{mid}/studio/open")
async def studio_open(mid: str, request: Request):
    require_display(request, "Solo dal display")
    _meta(mid)
    try:
        return studio.open_studio(mid)
    except studio.StudioError as exc:
        raise HTTPException(409, str(exc))


@public_routes.post("/api/models3d/{mid}/studio/close")
async def studio_close(mid: str, request: Request):
    require_display(request, "Solo dal display")
    _meta(mid)
    studio.close_studio()
    return {"ok": True}


@public_routes.post("/api/models3d/{mid}/studio/op")
async def studio_op(mid: str, request: Request):
    require_display(request, "Solo dal display")
    _meta(mid)
    body = await _body(request)
    try:
        return studio.operate(mid, body)
    except studio.StudioError as exc:
        raise HTTPException(400, str(exc))
    except (TypeError, ValueError) as exc:
        raise HTTPException(400, f"Richiesta non valida: {exc}")
