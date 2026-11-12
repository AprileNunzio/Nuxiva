import asyncio
import time

from fastapi import APIRouter, Depends, HTTPException

from access import require_admin
from agenti.nvr.archive import archive
from agenti.nvr.playback_api import _ids, camera_names
from agenti.nvr.search import has_time, parse, speech_terms
from agenti.nvr.service import nvr
from agenti.nvr.transcript_api import people_names

routes = APIRouter()
MAX_LIMIT = 100
SNIPPET = 280


def _snippets(hits: list[dict], transcripts) -> list[dict]:
    cache: dict[str, dict] = {}
    names = people_names()
    out = []
    for hit in hits:
        camera, segment, _ = hit["key"].split("|", 2)
        doc = f"{camera}|{segment}"
        if doc not in cache:
            cache[doc] = transcripts.load(camera, segment) or {}
        data = cache[doc]
        turn = next((t for t in data.get("turns", []) if int(t["start_ms"]) == hit["at_ms"]), None)
        if turn is None:
            continue
        out.append({"kind": "speech", "camera": camera, "segment": segment, "at_ms": hit["at_ms"],
                    "end_ms": int(turn["end_ms"]), "score": hit["score"], "text": str(turn["text"])[:SNIPPET],
                    "speaker": turn.get("speaker"), "speaker_name": names.get(turn.get("speaker") or "", ""),
                    "voice": turn.get("voice")})
    return out


def _events(q: str, camera: str | None, since_ms: int, until_ms: int, limit: int) -> list[dict]:
    query = parse(q)
    query = type(query)(max(query.since, since_ms / 1000), min(query.until, until_ms / 1000), query.labels, query.terms)
    if not query.labels and not query.terms:
        return []
    rows = []
    for row in nvr.store.search(query, MAX_LIMIT * 2):
        cam = row.get("camera_id") or ""
        if camera and cam != camera:
            continue
        found = archive.catalog.seek(cam, int(row["at"] * 1000)) if cam else None
        segment = found["segment"]["id"] if found and not found.get("gap_ms") else None
        rows.append({"kind": row["label"], "camera": cam, "segment": segment,
                     "at_ms": int(row["at"] * 1000), "score": float(row["score"]), "text": str(row["text"])[:SNIPPET],
                     "zone": row["zone"]})
        if len(rows) >= limit:
            break
    return rows


def find(q: str, camera: str | None, limit: int, now_ms: int | None = None) -> dict:
    from agenti.nvr.search_index import index
    now_ms = now_ms or int(time.time() * 1000)
    query = parse(q, now_ms / 1000)
    since, until = (int(query.since * 1000), int(query.until * 1000)) if has_time(q) else (0, now_ms + 86_400_000)
    words = speech_terms(q)
    speech = _snippets(index.search(words, camera, since, until, limit), index.transcripts) if words else []
    return {"q": q, "from_ms": since, "to_ms": until, "speech": speech,
            "events": _events(q, camera, since, until, limit), "cameras": camera_names()}


@routes.get("/api/nvr/find")
async def nvr_find(q: str, camera: str = "", limit: int = 40, _: str = Depends(require_admin)):
    q = q.strip()[:300]
    if not q:
        raise HTTPException(400, "nvr.query.empty")
    cam = _ids(camera)[0] if camera else None
    return await asyncio.to_thread(find, q, cam, max(1, min(MAX_LIMIT, limit)))


def segment_events(camera: str, segment: str) -> dict:
    from agenti.nvr.search_index import index
    row = archive.catalog.get(camera, segment)
    if row is None:
        raise HTTPException(404, "nvr.segment.missing")
    start, end = int(row["start_ms"]), int(row["start_ms"]) + int(row["duration_ms"])
    events = [{"kind": e["label"], "at_ms": int(e["at"] * 1000), "score": float(e["score"]), "text": str(e["text"])[:SNIPPET],
               "zone": e["zone"]} for e in nvr.store.between(camera, start / 1000, end / 1000, 500)]
    turns = (index.transcripts.load(camera, segment) or {}).get("turns", [])
    speech = [{"kind": "speech", "at_ms": int(t["start_ms"]), "end_ms": int(t["end_ms"]), "text": str(t["text"])[:SNIPPET],
               "speaker": t.get("speaker"), "voice": t.get("voice")} for t in turns]
    return {"camera": camera, "segment": segment, "start_ms": start, "end_ms": end,
            "items": sorted(events + speech, key=lambda i: i["at_ms"])}


@routes.get("/api/nvr/segments/{camera}/{segment}/events")
async def nvr_segment_events(camera: str, segment: str, _: str = Depends(require_admin)):
    camera, segment = _ids(camera, segment)
    return await asyncio.to_thread(segment_events, camera, segment)
