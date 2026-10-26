from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse

from access import require_admin
from state import store as state_store

from features.avatars import store

public_routes = APIRouter()
admin_routes = APIRouter()


@admin_routes.get("/api/avatars")
async def get_avatars(_: str = Depends(require_admin)):
    return store.listing()


@admin_routes.post("/api/avatars/active")
async def set_active_avatar(request: Request, user: str = Depends(require_admin)):
    body = await request.json()
    name = body.get("name") if isinstance(body, dict) else None
    if not isinstance(name, str):
        raise HTTPException(400, "Valore non valido")
    try:
        store.set_active(name)
    except store.AvatarError as exc:
        raise HTTPException(400, str(exc))
    state_store.event("INFO", f"Aspetto attivo: {name or 'predefinito'} ({user})", "avatars")
    return store.listing()


@admin_routes.post("/api/avatars/upload")
async def upload_avatar(name: str = Form(...), file: UploadFile = File(...), user: str = Depends(require_admin)):
    try:
        saved = store.save(name, file.filename or "", file.file)
    except store.AvatarError as exc:
        raise HTTPException(400, str(exc))
    finally:
        await file.close()
    state_store.event("INFO", f"Aspetto caricato: {saved['avatar']}/{saved['file']} ({user})", "avatars")
    return {**store.listing(), "saved": saved}


@admin_routes.delete("/api/avatars/{name}")
async def delete_avatar(name: str, user: str = Depends(require_admin)):
    try:
        store.remove(name)
    except store.AvatarError as exc:
        raise HTTPException(400, str(exc))
    state_store.event("INFO", f"Aspetto rimosso: {name} ({user})", "avatars")
    return store.listing()


@public_routes.get("/api/avatars/serve/{name}/{filename}")
async def serve_avatar_file(name: str, filename: str):
    try:
        path = store.resolve(name, filename)
    except store.AvatarError:
        raise HTTPException(400)
    except FileNotFoundError:
        raise HTTPException(404)
    ext = path.suffix.lower()
    media = ("model/gltf-binary" if ext == ".glb"
             else "application/octet-stream" if ext == ".fbx"
             else "image/png" if ext == ".png"
             else "image/jpeg" if ext in (".jpg", ".jpeg")
             else "image/webp" if ext == ".webp"
             else None)
    return FileResponse(path, media_type=media, headers={"Cache-Control": "private, max-age=300", "X-Content-Type-Options": "nosniff"})
