from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse

from access import require_admin
from features.nvr.service import nvr
from features.nvr.settings import SettingsError, public
from features.nvr.vault import VAULT_DIR, media_vault

admin_routes = APIRouter()
public_routes = APIRouter()


@admin_routes.get("/api/nvr/overview")
async def nvr_overview(_: str = Depends(require_admin)):
    return {**nvr.status(), "cameras": nvr.cameras()}


@admin_routes.get("/api/nvr/settings")
async def nvr_settings(_: str = Depends(require_admin)):
    return public(nvr.settings)


@admin_routes.put("/api/nvr/settings")
async def nvr_settings_update(request: Request, _: str = Depends(require_admin)):
    if int(request.headers.get("content-length") or 0) > 8192:
        raise HTTPException(413, "nvr.error.too_large")
    body = await request.json()
    if not isinstance(body, dict):
        raise HTTPException(400, "nvr.error.body")
    try:
        return nvr.update_settings(body)
    except SettingsError as exc:
        raise HTTPException(400, str(exc))


@admin_routes.get("/api/nvr/search")
async def nvr_search(q: str = "", limit: int = 50, _: str = Depends(require_admin)):
    return nvr.search(q[:300], limit)


@admin_routes.delete("/api/nvr/events")
async def nvr_clear(_: str = Depends(require_admin)):
    nvr.store.clear()
    nvr.publish_status()
    return {"ok": True}


@admin_routes.get("/api/nvr/media/{camera_id}/segments")
async def nvr_media_segments(camera_id: str, _: str = Depends(require_admin)):
    return {"camera_id": camera_id, "segments": media_vault.list_segments(camera_id)}


@admin_routes.get("/api/nvr/media/{camera_id}/stream/{segment_id}")
async def nvr_media_stream(camera_id: str, segment_id: str, _: str = Depends(require_admin)):
    clean_seg = "".join(c for c in segment_id if c.isalnum() or c in ("-", "_"))
    clean_cam = "".join(c for c in camera_id if c.isalnum() or c in ("-", "_"))
    seg_file = VAULT_DIR / clean_cam / f"{clean_seg}.nvm"
    if not seg_file.exists():
        raise HTTPException(404, "nvr.media.not_found")
    try:
        return StreamingResponse(
            media_vault.stream_chunks(clean_cam, seg_file),
            media_type="video/mp4",
            headers={"Content-Disposition": f'inline; filename="{clean_seg}.mp4"'}
        )
    except Exception as exc:
        raise HTTPException(500, f"nvr.media.stream_error: {exc}")
