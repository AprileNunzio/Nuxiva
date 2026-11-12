import asyncio
import time

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import Response, StreamingResponse

from access import require_admin
from agenti.nvr.archive import archive
from agenti.nvr.catalog import next_marker
from agenti.nvr.ranges import parse_range
from agenti.nvr.service import nvr
from agenti.nvr.vault import VaultError, clean_id

routes = APIRouter()
MAX_WINDOW_MS = 7 * 86_400_000
MAX_MARKERS = 5000
KINDS_MAX = 12
SECURE_HEADERS = {"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff",
                  "Cross-Origin-Resource-Policy": "same-origin"}


def _ids(*values: str) -> list[str]:
    try:
        return [clean_id(v) for v in values]
    except VaultError:
        raise HTTPException(400, "nvr.id.invalid")


def _window(from_ms: int, to_ms: int) -> tuple[int, int]:
    if to_ms <= from_ms or to_ms - from_ms > MAX_WINDOW_MS or from_ms < 0:
        raise HTTPException(400, "nvr.window.invalid")
    return from_ms, to_ms


def camera_names() -> dict[str, dict]:
    try:
        from agenti.cameras.cameras import cameras
    except ImportError:
        return {}
    return {cid: {"name": str(cam.get("name") or cid), "room": str(cam.get("room") or "")}
            for cid, cam in cameras.items.items()}


def markers(camera: str, from_ms: int, to_ms: int) -> list[dict]:
    rows = nvr.store.between(camera, from_ms / 1000, to_ms / 1000, MAX_MARKERS)
    out = [{"at_ms": int(r["at"] * 1000), "camera": camera, "kind": str(r["label"])[:40], "id": str(r["id"])[:80],
            "label": str(r["text"])[:200], "score": float(r["score"])} for r in rows]
    try:
        from agenti.nvr.transcripts import transcript_markers
        out += transcript_markers(camera, from_ms, to_ms)
    except ImportError:
        pass
    return sorted(out, key=lambda m: (m["at_ms"], m["id"]))[:MAX_MARKERS]


@routes.get("/api/nvr/recordings")
async def nvr_recordings(_: str = Depends(require_admin)):
    names = camera_names()
    rows = await asyncio.to_thread(archive.catalog.summary)
    return {"cameras": [{**r, **names.get(r["camera"], {"name": r["camera"], "room": ""})} for r in rows],
            "now_ms": int(time.time() * 1000)}


@routes.get("/api/nvr/timeline")
async def nvr_timeline(camera: str, from_ms: int, to_ms: int, _: str = Depends(require_admin)):
    (camera,) = _ids(camera)
    from_ms, to_ms = _window(from_ms, to_ms)
    segments = await asyncio.to_thread(archive.catalog.range, camera, from_ms, to_ms, 20_000)
    spans = await asyncio.to_thread(archive.catalog.spans, camera, from_ms, to_ms)
    marks = await asyncio.to_thread(markers, camera, from_ms, to_ms)
    return {"camera": camera, "from_ms": from_ms, "to_ms": to_ms, "spans": spans, "markers": marks,
            "segments": [{k: s[k] for k in ("id", "start_ms", "duration_ms", "tier", "audio", "video", "bytes")}
                         for s in segments]}


@routes.get("/api/nvr/seek")
async def nvr_seek(camera: str, at_ms: int, _: str = Depends(require_admin)):
    (camera,) = _ids(camera)
    found = await asyncio.to_thread(archive.catalog.seek, camera, max(0, at_ms))
    if found is None:
        raise HTTPException(404, "nvr.seek.nothing")
    return found


@routes.get("/api/nvr/jump")
async def nvr_jump(camera: str, at_ms: int, direction: str = "next", kinds: str = "",
                   _: str = Depends(require_admin)):
    (camera,) = _ids(camera)
    wanted = [k.strip()[:40] for k in kinds.split(",") if k.strip()][:KINDS_MAX]
    forward = direction != "prev"
    low, high = (at_ms, at_ms + MAX_WINDOW_MS) if forward else (max(0, at_ms - MAX_WINDOW_MS), at_ms + 1)
    marks = await asyncio.to_thread(markers, camera, low, high)
    hit = next_marker(marks, at_ms, forward, wanted)
    if hit is None:
        raise HTTPException(404, "nvr.jump.nothing")
    seek = await asyncio.to_thread(archive.catalog.seek, camera, max(0, hit["at_ms"] - 3000))
    return {"marker": hit, "seek": seek}


@routes.get("/api/nvr/next/{camera}/{segment}")
async def nvr_next_segment(camera: str, segment: str, _: str = Depends(require_admin)):
    camera, segment = _ids(camera, segment)
    found = await asyncio.to_thread(archive.catalog.after, camera, segment)
    if found is None:
        raise HTTPException(404, "nvr.segment.last")
    return found


@routes.get("/api/nvr/play/{camera}/{segment}")
async def nvr_play(camera: str, segment: str, request: Request, _: str = Depends(require_admin)):
    camera, segment = _ids(camera, segment)
    path = archive.vault.path_for(camera, segment)
    if not path.is_file():
        raise HTTPException(404, "nvr.media.not_found")
    try:
        info = await asyncio.to_thread(archive.vault.header, path)
    except (OSError, ValueError):
        raise HTTPException(422, "nvr.media.unreadable")
    if info is None:
        data = await asyncio.to_thread(archive.vault.decrypt_file, camera, path)
        return Response(data, media_type="video/mp4", headers=SECURE_HEADERS)
    total = int(info["plain_bytes"])
    kind, start, end = parse_range(request.headers.get("range", ""), total)
    if kind == "invalid":
        raise HTTPException(416, "nvr.range.invalid", headers={"Content-Range": f"bytes */{total}"})
    headers = {**SECURE_HEADERS, "Accept-Ranges": "bytes", "Content-Length": str(end - start + 1 if total else 0),
               "Content-Disposition": f'inline; filename="{segment}.mp4"'}
    status = 200
    if kind == "part":
        status = 206
        headers["Content-Range"] = f"bytes {start}-{end}/{total}"
    body = archive.vault.read_range(camera, path, start, end) if total else iter(())
    return StreamingResponse(body, status_code=status, media_type="video/mp4", headers=headers)


@routes.post("/api/nvr/segments/{camera}/{segment}/pin")
async def nvr_pin(camera: str, segment: str, request: Request, _: str = Depends(require_admin)):
    camera, segment = _ids(camera, segment)
    if int(request.headers.get("content-length") or 0) > 256:
        raise HTTPException(413, "nvr.error.too_large")
    body = await request.json()
    pinned = bool(body.get("pinned")) if isinstance(body, dict) else False
    try:
        return await asyncio.to_thread(archive.pin, camera, segment, pinned)
    except VaultError as exc:
        raise HTTPException(404, str(exc))


@routes.delete("/api/nvr/segments/{camera}/{segment}")
async def nvr_delete_segment(camera: str, segment: str, _: str = Depends(require_admin)):
    camera, segment = _ids(camera, segment)
    gone = await asyncio.to_thread(archive.delete, camera, segment)
    if not gone:
        raise HTTPException(404, "nvr.segment.not_found")
    return {"ok": True}


@routes.get("/api/nvr/markers")
async def nvr_markers(camera: str, from_ms: int, to_ms: int, kinds: list[str] = Query(default=[]),
                      _: str = Depends(require_admin)):
    (camera,) = _ids(camera)
    from_ms, to_ms = _window(from_ms, to_ms)
    rows = await asyncio.to_thread(markers, camera, from_ms, to_ms)
    wanted = {k[:40] for k in kinds[:KINDS_MAX]}
    return {"markers": [m for m in rows if not wanted or m["kind"] in wanted]}
