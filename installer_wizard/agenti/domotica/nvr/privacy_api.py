import asyncio
import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse

from access import NO_CACHE, require_admin

from agenti.nvr import privacy
from agenti.nvr.notice import notice
from agenti.nvr.playback_api import camera_names
from agenti.nvr.service import nvr
from agenti.nvr.settings import SettingsError

log = logging.getLogger("nuxiva.nvr.privacy_api")
routes = APIRouter()
KEYS = ("audio_cameras", "notice_enabled", "notice_repeat_hours", "private_rooms")
MAX_BODY = 8192


def _cameras() -> list[dict]:
    return [{"id": cid, **row} for cid, row in sorted(camera_names().items())]


def _audit(action: str, slug: str, details: dict) -> None:
    try:
        from agenti.sentinel import record
        record.record("sentinel.read", record.NUXIVA, f"sentinel.nvr.{action}", {"slug": slug, **details}, "sensitive", "nvr")
    except (ImportError, OSError, ValueError, RuntimeError) as exc:
        log.warning("NVR: operazione %s non annotata nel registro: %s", action, exc)


def state() -> dict:
    return {**privacy.overview(_cameras(), nvr.settings), "notice": notice.status()}


async def _body(request: Request) -> dict:
    if int(request.headers.get("content-length") or 0) > MAX_BODY:
        raise HTTPException(413, "nvr.error.too_large")
    body = await request.json()
    if not isinstance(body, dict):
        raise HTTPException(400, "nvr.error.body")
    return body


@routes.get("/api/nvr/privacy")
async def nvr_privacy(_: str = Depends(require_admin)):
    return JSONResponse(await asyncio.to_thread(state), headers=NO_CACHE)


@routes.put("/api/nvr/privacy")
async def nvr_privacy_update(request: Request, _: str = Depends(require_admin)):
    body = await _body(request)
    try:
        nvr.update_settings({k: body[k] for k in KEYS if k in body})
    except SettingsError as exc:
        raise HTTPException(400, str(exc)) from exc
    return JSONResponse(await asyncio.to_thread(state), headers=NO_CACHE)


@routes.post("/api/nvr/notice/announce")
async def nvr_notice_announce(_: str = Depends(require_admin)):
    current = await asyncio.to_thread(state)
    entry = notice.tick(current["cameras"], nvr.settings, force=True)
    if entry is None:
        raise HTTPException(409, "nvr.notice.nothing_to_announce")
    return entry


def _deps():
    from agenti.nvr.archive import archive
    from agenti.nvr.search_index import index
    return archive, index


@routes.get("/api/nvr/privacy/person/{slug}")
async def nvr_privacy_export(slug: str, _: str = Depends(require_admin)):
    _, index = _deps()
    try:
        data = await asyncio.to_thread(privacy.export_person, slug, index.transcripts)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    _audit("export", slug, {"count": len(data["turns"])})
    return JSONResponse(data, headers={**NO_CACHE, "Content-Disposition": f'attachment; filename="nvr-{slug}.json"'})


@routes.post("/api/nvr/privacy/person/{slug}/erase")
async def nvr_privacy_erase(slug: str, request: Request, _: str = Depends(require_admin)):
    body = await _body(request)
    archive, index = _deps()
    try:
        result = await asyncio.to_thread(privacy.erase_person, slug, index.transcripts, index, archive,
                                         bool(body.get("delete_segments")))
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    _audit("erase", slug, {"count": result["turns_removed"], "deleted": result["segments_deleted"]})
    return JSONResponse(result, headers=NO_CACHE)
