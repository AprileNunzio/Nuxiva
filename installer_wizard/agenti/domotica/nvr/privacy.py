import logging
import re
import time

import native_module
from agenti.nvr import policy_py

log = logging.getLogger("nuxiva.nvr.privacy")
SLUG = re.compile(r"^[a-z0-9_.-]{1,64}$")
MAX_EXPORT_TURNS = 50_000


def audio_decision(room: str, opted_in: bool, notice_active: bool, extra: list[str]) -> tuple[bool, str, bool]:
    fn = native_module.feature("nvr_audio_decision")
    if fn is None:
        native_module.python_fallback("nvr.audio_policy")
        return policy_py.py_audio_decision(room, opted_in, notice_active, extra)
    allowed, reason, private = fn(str(room), bool(opted_in), bool(notice_active), [str(e) for e in extra])
    return bool(allowed), str(reason), bool(private)


def camera_audio(cam: dict, settings: dict) -> dict:
    allowed, reason, private = audio_decision(str(cam.get("room") or ""), cam.get("id") in settings.get("audio_cameras", []),
                                              bool(settings.get("notice_enabled")), list(settings.get("private_rooms", [])))
    return {"camera": cam.get("id"), "name": str(cam.get("name") or cam.get("id")), "room": str(cam.get("room") or ""),
            "opted_in": cam.get("id") in settings.get("audio_cameras", []), "private": private, "allowed": allowed,
            "reason": reason}


def overview(cameras: list[dict], settings: dict) -> dict:
    rows = [camera_audio(c, settings) for c in cameras]
    return {"notice_enabled": bool(settings.get("notice_enabled")), "notice_repeat_hours": settings.get("notice_repeat_hours", 12),
            "private_rooms": list(settings.get("private_rooms", [])), "cameras": rows,
            "recording_audio": [r["camera"] for r in rows if r["allowed"]]}


def _documents(transcripts):
    root = transcripts.root
    for path in sorted(root.glob("*/*.nvb")) if root.exists() else []:
        try:
            data = transcripts.load(path.parent.name, path.stem)
        except (OSError, ValueError) as exc:
            log.warning("NVR: trascrizione %s esclusa: %s", path.name, exc)
            continue
        if data:
            yield path.parent.name, path.stem, data


def export_person(slug: str, transcripts) -> dict:
    if not SLUG.match(slug):
        raise ValueError("invalid_slug")
    turns = []
    for camera, segment, data in _documents(transcripts):
        for t in data.get("turns", []):
            if t.get("speaker") == slug and len(turns) < MAX_EXPORT_TURNS:
                turns.append({"camera": camera, "segment": segment, "start_ms": int(t["start_ms"]),
                              "end_ms": int(t["end_ms"]), "text": str(t["text"])})
    return {"slug": slug, "exported_at": int(time.time() * 1000), "segments": sorted({f"{t['camera']}/{t['segment']}" for t in turns}),
            "turns": sorted(turns, key=lambda t: t["start_ms"])}


def erase_person(slug: str, transcripts, index, archive=None, delete_segments: bool = False) -> dict:
    if not SLUG.match(slug):
        raise ValueError("invalid_slug")
    removed_turns, touched, deleted = 0, 0, 0
    for camera, segment, data in list(_documents(transcripts)):
        turns = data.get("turns", [])
        kept = [t for t in turns if t.get("speaker") != slug]
        if len(kept) == len(turns):
            continue
        removed_turns += len(turns) - len(kept)
        touched += 1
        if delete_segments and archive is not None:
            if archive.delete(camera, segment):
                deleted += 1
            transcripts.delete(camera, segment)
            index.forget(camera, segment)
            continue
        transcripts.save(camera, segment, {**data, "turns": kept})
        index.index_transcript(camera, segment, kept)
    index.save(force=True)
    return {"slug": slug, "turns_removed": removed_turns, "segments_touched": touched, "segments_deleted": deleted}
