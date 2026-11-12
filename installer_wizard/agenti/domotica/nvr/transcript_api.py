import asyncio

from fastapi import APIRouter, Depends, HTTPException

from access import require_admin
from agenti.nvr.playback_api import _ids, _window, camera_names
from agenti.nvr.transcripts import room_transcript

routes = APIRouter()


def people_names() -> dict[str, str]:
    try:
        from agenti.people import people
    except ImportError:
        return {}
    return {p["slug"]: str(p.get("name") or p["slug"]) for p in people.all_profiles(light=True) if p.get("slug")}


def room_cameras(camera: str) -> dict[str, float]:
    names = camera_names()
    room = names.get(camera, {}).get("room", "")
    if not room:
        return {camera: 1.0}
    return {cid: 1.0 for cid, row in names.items() if row.get("room") == room} | {camera: 1.0}


@routes.get("/api/nvr/transcript")
async def nvr_transcript(camera: str, from_ms: int, to_ms: int, _: str = Depends(require_admin)):
    (camera,) = _ids(camera)
    from_ms, to_ms = _window(from_ms, to_ms)
    if to_ms - from_ms > 86_400_000:
        raise HTTPException(400, "nvr.window.invalid")
    sources = room_cameras(camera)
    turns = await asyncio.to_thread(room_transcript, sources, from_ms, to_ms)
    names = await asyncio.to_thread(people_names)
    return {"camera": camera, "sources": sorted(sources), "turns": [
        {**t, "speaker_name": names.get(t["speaker"] or "", "")} for t in turns]}
