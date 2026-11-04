from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse, JSONResponse

from access import NO_CACHE, require_admin

from features.backup import service

admin_routes = APIRouter()


def _known(backup_id: str) -> str:
    if not service.ID_RE.fullmatch(backup_id):
        raise HTTPException(404, "Backup sconosciuto")
    return backup_id


@admin_routes.get("/api/backup")
async def backup_status(_: str = Depends(require_admin)):
    return JSONResponse(service.status(), headers=NO_CACHE)


@admin_routes.post("/api/backup")
async def backup_create(_: str = Depends(require_admin)):
    if not service.enabled():
        raise HTTPException(409, "I backup sono disattivati")
    try:
        return JSONResponse(await service.create(), headers=NO_CACHE)
    except OSError as exc:
        raise HTTPException(500, f"Backup non riuscito: {exc}")


@admin_routes.post("/api/backup/{backup_id}/verify")
async def backup_verify(backup_id: str, _: str = Depends(require_admin)):
    try:
        return JSONResponse(await service.verify(_known(backup_id)), headers=NO_CACHE)
    except KeyError:
        raise HTTPException(404, "Backup sconosciuto")


@admin_routes.get("/api/backup/{backup_id}/download")
async def backup_download(backup_id: str, _: str = Depends(require_admin)):
    try:
        path = service.path_of(_known(backup_id))
    except KeyError:
        raise HTTPException(404, "Backup sconosciuto")
    return FileResponse(path, media_type="application/gzip", filename=path.name, headers=NO_CACHE)


@admin_routes.delete("/api/backup/{backup_id}")
async def backup_delete(backup_id: str, _: str = Depends(require_admin)):
    try:
        service.delete(_known(backup_id))
    except KeyError:
        raise HTTPException(404, "Backup sconosciuto")
    return {"ok": True}
