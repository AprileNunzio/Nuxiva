from fastapi import APIRouter, Depends, HTTPException, Request

from access import require_admin

admin_routes = APIRouter()
public_routes = APIRouter()
MAX_BODY = 16 * 1024


@admin_routes.get("/api/display/surfaces")
async def display_surfaces(_: str = Depends(require_admin)):
    from agenti.desktop.screens import screens
    from agenti.desktop.surfaces import strict, surfaces
    active = screens.active()
    return {"poses": {str(k): v for k, v in sorted(surfaces.poses().items())}, "screens": surfaces.annotate(active),
            "sensed_rooms": surfaces.sensed_rooms(), "strict": strict()}


@admin_routes.put("/api/display/surfaces")
async def display_surfaces_save(request: Request, _: str = Depends(require_admin)):
    raw = await request.body()
    if len(raw) > MAX_BODY:
        raise HTTPException(413, "Configurazione troppo grande")
    try:
        body = await request.json()
    except ValueError:
        raise HTTPException(400, "Configurazione non valida")
    from agenti.desktop.screens import screens
    from agenti.desktop.surfaces import surfaces
    try:
        saved = surfaces.save(body.get("poses") if isinstance(body, dict) else None)
    except ValueError as exc:
        raise HTTPException(422, str(exc))
    screens.publish()
    return {"ok": True, "poses": {str(k): v for k, v in sorted(saved.items())}}
