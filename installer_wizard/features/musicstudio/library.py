import logging
import time

from features.music import layout, lyrics_store, naming, tagwriter
from features.musicstudio import schema as S, store

log = logging.getLogger("nuxiva.musicstudio")
ARTIST = "Nuxiva Studio"
ALBUM = "Studio Musicale"


def tags(project: dict) -> dict:
    title = project["title"] or project["prompt"] or "Canzone"
    return {"title": S.text(title, 90), "artist": ARTIST, "album_artist": ARTIST, "album": ALBUM, "genre": project["genre"].title(), "year": time.gmtime(project["created"]).tm_year if project["created"] else 0, "track_no": 0}


def publish(project: dict, wav: bytes) -> str:
    info = tags(project)
    target = naming.destination(info, ".wav")
    if target is None:
        raise OSError("library_unavailable")
    previous = store.published(project["id"])
    existing = (layout.root() / previous) if previous else None
    if existing is not None and existing.is_file() and layout.root() in existing.resolve().parents:
        target = existing
    target.parent.mkdir(parents=True, exist_ok=True)
    target = target if target == existing else _free(target, project["id"])
    target.write_bytes(wav)
    tagwriter.write(target, info)
    text = project["lyrics"]["text"]
    if text:
        lyrics_store.sidecar(target.relative_to(layout.root()).as_posix()).write_text(lyrics_store.to_lrc({"plain": text}), encoding="utf-8")
    store.set_published(project["id"], target.relative_to(layout.root()).as_posix())
    _rescan()
    return target.relative_to(layout.root()).as_posix()


def _free(target, pid: str):
    if not target.exists():
        return target
    return target.with_name(f"{target.stem} [{pid}]{target.suffix}")


def _rescan() -> None:
    try:
        from features.music.service import library
        library.trigger()
    except RuntimeError as exc:
        log.info("musicstudio: rescan skipped (%s)", type(exc).__name__)


def track_id(pid: str) -> int | None:
    from features.music.db import db
    relative = store.published(pid)
    if not relative:
        return None
    row = db.row("SELECT id FROM tracks WHERE path=?", (relative,))
    return int(row["id"]) if row else None


def ensure_indexed(pid: str) -> int | None:
    found = track_id(pid)
    if found is None and store.published(pid):
        from features.music import scanner
        scanner.scan()
        found = track_id(pid)
    return found
