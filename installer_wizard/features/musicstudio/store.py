import json
import shutil
import threading

from config import STATE_DIR
from sealed import write_private

from features.musicstudio import schema as S

DIRECTORY = STATE_DIR / "musicstudio"
MAX_PROJECTS = 80
lock = threading.RLock()


def _dir(pid: str):
    if not S.ID_RE.fullmatch(pid):
        raise KeyError(pid)
    return DIRECTORY / pid


def _read(path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        raise KeyError(path.name)


def _compact(value) -> bytes:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode()


def _write(path, payload: bytes) -> None:
    try:
        if path.read_bytes() == payload:
            return
    except OSError:
        pass
    write_private(path, payload)


def load(pid: str) -> dict:
    folder = _dir(pid)
    meta = _read(folder / "meta.json")
    if not isinstance(meta, dict):
        raise KeyError(pid)
    order = meta.get("track_order") if isinstance(meta.get("track_order"), list) else []
    tracks = []
    for tid in order[:S.MAX_TRACKS]:
        if isinstance(tid, str) and S.ID_RE.fullmatch(tid):
            try:
                tracks.append(_read(folder / "tracks" / f"{tid}.json"))
            except KeyError:
                continue
    return S.clean_project({**meta, "tracks": tracks}, pid)


def save(project: dict) -> None:
    with lock:
        folder = _dir(project["id"])
        (folder / "tracks").mkdir(parents=True, exist_ok=True)
        meta = {k: v for k, v in project.items() if k != "tracks"}
        meta["track_order"] = [t["id"] for t in project["tracks"]]
        _write(folder / "meta.json", _compact(meta))
        keep = set()
        for track in project["tracks"]:
            keep.add(f"{track['id']}.json")
            _write(folder / "tracks" / f"{track['id']}.json", _compact(track))
        for stale in (folder / "tracks").glob("*.json"):
            if stale.name not in keep:
                stale.unlink()


def remove(pid: str) -> None:
    with lock:
        folder = _dir(pid)
        if not folder.is_dir():
            raise KeyError(pid)
        shutil.rmtree(folder, ignore_errors=True)


def ids() -> list[str]:
    if not DIRECTORY.exists():
        return []
    return sorted(p.name for p in DIRECTORY.iterdir() if p.is_dir() and S.ID_RE.fullmatch(p.name))


def listing() -> list[dict]:
    rows = []
    for pid in ids():
        try:
            meta = _read(_dir(pid) / "meta.json")
        except KeyError:
            continue
        rows.append({"id": pid, "title": S.text(meta.get("title"), 80), "genre": meta.get("genre"), "tempo": meta.get("tempo"), "bars": meta.get("bars"),
                     "created": int(meta.get("created") or 0), "tracks": len(meta.get("track_order") or [])})
    return sorted(rows, key=lambda r: r["created"], reverse=True)[:MAX_PROJECTS]


def audio_dir(pid: str):
    folder = _dir(pid) / "audio"
    folder.mkdir(parents=True, exist_ok=True)
    return folder
