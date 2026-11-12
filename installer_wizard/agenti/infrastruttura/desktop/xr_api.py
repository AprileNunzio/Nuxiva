from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse

from access import require_admin

public_routes = APIRouter()
admin_routes = APIRouter()
MANAGE = {"x-nuxiva-capabilities": ["devices.manage"]}
MAX_BODY = 2048


def _device(request: Request) -> str:
    from agenti.desktop.xr_pairing import COOKIE, pairing
    device_id = pairing.authenticate(request.cookies.get(COOKIE))
    if device_id is None:
        raise HTTPException(401, "Visore non accoppiato")
    return device_id


def xr_device(request: Request) -> str | None:
    from agenti.desktop.xr_pairing import COOKIE, pairing
    return pairing.authenticate(request.cookies.get(COOKIE))


async def _json(request: Request) -> dict:
    raw = await request.body()
    if len(raw) > MAX_BODY:
        raise HTTPException(413, "Richiesta troppo grande")
    try:
        body = await request.json()
    except ValueError:
        raise HTTPException(400, "Richiesta non valida")
    if not isinstance(body, dict):
        raise HTTPException(400, "Richiesta non valida")
    return body


@public_routes.get("/xr")
async def xr_page(request: Request):
    from pages import page
    from agenti.locale.api import page_language
    return page("display/xr/xr.html", page_language(request, admin=False))


@public_routes.post("/api/xr/redeem")
async def xr_redeem(request: Request):
    from agenti.desktop.xr_pairing import COOKIE, TOKEN_TTL, pairing
    from state import store
    body = await _json(request)
    try:
        token = pairing.redeem(str(body.get("code") or "")[:16], str(body.get("device") or ""), body.get("name"))
    except PermissionError as exc:
        store.event("WARN", "Accoppiamento di un visore rifiutato", "xr")
        raise HTTPException(403, str(exc))
    except ValueError as exc:
        raise HTTPException(422, str(exc))
    store.event("INFO", "Nuovo visore accoppiato", "xr")
    res = JSONResponse({"ok": True})
    res.set_cookie(COOKIE, token, max_age=TOKEN_TTL, httponly=True, samesite="strict",
                   secure=request.url.scheme == "https", path="/")
    return res


@public_routes.get("/api/xr/scene")
async def xr_scene(request: Request):
    device_id = _device(request)
    from agenti.desktop.audience_view import item_visible
    from agenti.desktop.desk import desk
    from agenti.desktop.presence_bridge import bridge, show_options
    from agenti.desktop.surfaces import surfaces
    from agenti.desktop.xr_pairing import pairing
    device = pairing.device(device_id) or {}
    kind = surfaces.audience_in(device.get("room"), bridge.last.get("kind", "uncertain"))
    panels = []
    if kind == "authorized":
        show = show_options()
        for item in desk.active():
            if not item_visible(kind, item, show):
                continue
            data = item.get("data") if isinstance(item.get("data"), dict) else {}
            panel = {"key": str(item.get("key") or "")[:120], "id": item["id"], "name": str(item.get("name") or "")[:60],
                     "icon": str(item.get("icon") or "")[:8]}
            if item["id"] == "molecule_viewer" and isinstance(data.get("id"), str):
                panel["molecule"] = data["id"][:16]
            panels.append(panel)
    return {"device": {"name": device.get("name"), "room": device.get("room")}, "audience": kind,
            "nucleus_only": kind != "authorized", "panels": panels[:12]}


@admin_routes.post("/api/xr/pair", openapi_extra=MANAGE)
async def xr_pair(user: str = Depends(require_admin)):
    from agenti.desktop.xr_pairing import pairing
    issued = pairing.issue(user)
    return {**issued, "path": f"/xr?pair={issued['code']}"}


@admin_routes.get("/api/xr/devices", openapi_extra=MANAGE)
async def xr_devices(_: str = Depends(require_admin)):
    from agenti.desktop.xr_pairing import pairing
    return {"devices": pairing.listing()}


@admin_routes.put("/api/xr/devices/{device_id}", openapi_extra=MANAGE)
async def xr_device_update(device_id: str, request: Request, _: str = Depends(require_admin)):
    from agenti.desktop.surfaces import ROOM, slug
    from agenti.desktop.xr_pairing import pairing
    body = await _json(request)
    room = slug(body.get("room")) if body.get("room") else None
    if room is not None and not ROOM.match(room):
        raise HTTPException(422, "Stanza non valida")
    try:
        pairing.set_room(device_id, room)
    except KeyError:
        raise HTTPException(404, "Visore sconosciuto")
    return {"ok": True, "room": room}


@admin_routes.delete("/api/xr/devices/{device_id}", openapi_extra=MANAGE)
async def xr_revoke(device_id: str, user: str = Depends(require_admin)):
    from agenti.desktop.xr_pairing import pairing
    from state import store
    try:
        pairing.revoke(device_id)
    except KeyError:
        raise HTTPException(404, "Visore sconosciuto")
    store.event("INFO", f"Visore revocato da {user}", "xr")
    return {"ok": True}
