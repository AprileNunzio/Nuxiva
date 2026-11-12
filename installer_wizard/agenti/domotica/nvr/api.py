import asyncio
import time

from fastapi import APIRouter, Depends, HTTPException, Request

from access import require_admin
from agenti.nvr.service import nvr
from agenti.nvr.settings import SettingsError, public
from agenti.nvr.playback_api import routes as playback_routes
from agenti.nvr.transcript_api import routes as transcript_routes
from agenti.nvr.vault import media_vault

admin_routes = APIRouter()
public_routes = APIRouter()
admin_routes.include_router(playback_routes)
admin_routes.include_router(transcript_routes)


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


@admin_routes.get("/api/nvr/storage")
async def nvr_storage(_: str = Depends(require_admin)):
    percent = float(nvr.settings.get("storage_percent", 20))
    max_gb = float(nvr.settings.get("storage_max_gb", 0))
    return media_vault.storage_stats(percent, max_gb)


@admin_routes.post("/api/nvr/prune")
async def nvr_prune(_: str = Depends(require_admin)):
    from agenti.cameras.cameras import cameras
    from agenti.nvr.archive import archive
    events = nvr.store.camera_times(time.time() - int(nvr.settings.get("retention_days", 30)) * 86400)
    wanted = {cid: cam for cid, cam in cameras.items.items() if cameras._recording(cam)}
    done = await asyncio.to_thread(archive.maintain, events, nvr.settings, wanted)
    return {"ok": True, "freed_segments": done["removed"], **done}


@admin_routes.get("/api/nvr/ptz/cameras")
async def nvr_ptz_cameras(_: str = Depends(require_admin)):
    from agenti.cameras.ptz import ptz
    return {"cameras": ptz.list_ptz_cameras()}


@admin_routes.post("/api/nvr/ptz/control")
async def nvr_ptz_control(request: Request, _: str = Depends(require_admin)):
    from agenti.cameras.ptz import ptz
    body = await request.json()
    if not isinstance(body, dict):
        raise HTTPException(400, "nvr.error.body")
    cam_id = str(body.get("camera_id") or "")
    action = str(body.get("action") or "move").lower()
    if action == "stop":
        return ptz.stop(cam_id)
    if action == "preset":
        return ptz.goto_preset(cam_id, body.get("preset", "home"))
    if action == "patrol_start":
        interval = int(body.get("interval", 60))
        return {"ok": ptz.start_patrol(cam_id, interval)}
    if action == "patrol_stop":
        return {"ok": ptz.stop_patrol(cam_id)}
    if action == "track":
        box = body.get("box") or [0.5, 0.5, 0.1, 0.1]
        return ptz.track(cam_id, box)
    pan = float(body.get("pan", 0.0))
    tilt = float(body.get("tilt", 0.0))
    zoom = float(body.get("zoom", 0.0))
    speed = float(body.get("speed", 0.5))
    return ptz.move(cam_id, pan, tilt, zoom, speed)


@admin_routes.get("/api/nvr/events/{event_id}/details")
async def nvr_event_details(event_id: str, _: str = Depends(require_admin)):
    ev = nvr.store.get(event_id)
    if not ev:
        raise HTTPException(404, "nvr.event.not_found")
    return ev


@admin_routes.post("/api/nvr/analyze/{camera_id}/{segment_id}")
async def nvr_analyze_segment(camera_id: str, segment_id: str, _: str = Depends(require_admin)):
    from agenti.nvr.analyzer import analyzer
    res = analyzer.analyze_segment(camera_id, segment_id)
    return res
