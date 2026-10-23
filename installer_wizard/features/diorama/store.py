import json
import shutil
import threading

from config import STATE_DIR
from sealed import write_private

from features.diorama import spec as S

DIRECTORY = STATE_DIR / "diorama"
MAX_DIORAMAS = 60
META = "meta"
lock = threading.RLock()


def _dir(did: str):
    if not S.ID_RE.fullmatch(did):
        raise KeyError(did)
    return DIRECTORY / did


def _legacy(did: str):
    return DIRECTORY / f"{did}.json"


def _read(path) -> dict | list:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        raise KeyError(path.name)


def _compact(value) -> bytes:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode()


def _raw(did: str) -> dict:
    folder = _dir(did)
    if folder.is_dir():
        data = _read(folder / f"{META}.json")
        if not isinstance(data, dict):
            raise KeyError(did)
        items = []
        for layer in S.LAYERS:
            part = folder / f"{layer}.json"
            if part.is_file():
                rows = _read(part)
                items += rows if isinstance(rows, list) else []
        return {**data, "items": items}
    data = _read(_legacy(did))
    if not isinstance(data, dict):
        raise KeyError(did)
    return data


def load(did: str) -> dict:
    data = _raw(did)
    return {"id": did, "title": S.clean_text(data.get("title"), 80), "story": S.clean_text(data.get("story"), 400),
            "prompt": S.clean_text(data.get("prompt"), 600), "created": int(data.get("created") or 0),
            "base": S.clean_base(data.get("base")), "look": S.clean_look(data.get("look")), "items": S.clean_items(data.get("items")),
            "revision": int(data.get("revision") or 0), "ambient": bool(data.get("ambient")), "brief": S.clean_brief(data.get("brief"))}


def _write(path, payload: bytes) -> None:
    try:
        if path.read_bytes() == payload:
            return
    except OSError:
        pass
    write_private(path, payload)


def save(record: dict) -> None:
    with lock:
        folder = _dir(record["id"])
        folder.mkdir(parents=True, exist_ok=True)
        _write(folder / f"{META}.json", _compact({k: v for k, v in record.items() if k not in ("id", "items")}))
        for layer in S.LAYERS:
            rows = [i for i in record["items"] if i.get("layer", "user") == layer]
            part = folder / f"{layer}.json"
            if rows:
                _write(part, _compact(rows))
            elif part.exists():
                part.unlink()
        _legacy(record["id"]).unlink(missing_ok=True)


def remove(did: str) -> None:
    with lock:
        folder, legacy = _dir(did), _legacy(did)
        if not folder.is_dir() and not legacy.is_file():
            raise KeyError(did)
        shutil.rmtree(folder, ignore_errors=True)
        legacy.unlink(missing_ok=True)


def _ids() -> list[str]:
    if not DIRECTORY.exists():
        return []
    found = {p.name for p in DIRECTORY.iterdir() if p.is_dir()} | {p.stem for p in DIRECTORY.glob("*.json")}
    return sorted(i for i in found if S.ID_RE.fullmatch(i))


def listing() -> list[dict]:
    rows = []
    for did in _ids():
        try:
            record = load(did)
        except KeyError:
            continue
        rows.append({"id": did, "title": record["title"], "created": record["created"], "count": len(record["items"])})
    return sorted(rows, key=lambda r: r["created"], reverse=True)[:MAX_DIORAMAS]


def count() -> int:
    return len(_ids())


def prune_ambient(keep: int = 10) -> None:
    rows = []
    for did in _ids():
        try:
            record = load(did)
        except KeyError:
            continue
        if record["ambient"]:
            rows.append(record)
    for stale in sorted(rows, key=lambda r: r["created"], reverse=True)[keep:]:
        try:
            remove(stale["id"])
        except KeyError:
            continue
