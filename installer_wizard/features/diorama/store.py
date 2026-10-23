import json
import threading

from config import STATE_DIR
from sealed import write_private

from features.diorama import spec as S

DIRECTORY = STATE_DIR / "diorama"
MAX_DIORAMAS = 60
lock = threading.RLock()


def _path(did: str):
    if not S.ID_RE.fullmatch(did):
        raise KeyError(did)
    return DIRECTORY / f"{did}.json"


def load(did: str) -> dict:
    try:
        data = json.loads(_path(did).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        raise KeyError(did)
    if not isinstance(data, dict):
        raise KeyError(did)
    return {"id": did, "title": S.clean_text(data.get("title"), 80), "story": S.clean_text(data.get("story"), 400),
            "prompt": S.clean_text(data.get("prompt"), 600), "created": int(data.get("created") or 0),
            "base": S.clean_base(data.get("base")), "look": S.clean_look(data.get("look")), "items": S.clean_items(data.get("items")),
            "revision": int(data.get("revision") or 0), "ambient": bool(data.get("ambient")), "brief": S.clean_brief(data.get("brief"))}


def save(record: dict) -> None:
    with lock:
        DIRECTORY.mkdir(parents=True, exist_ok=True)
        write_private(_path(record["id"]), json.dumps({k: v for k, v in record.items() if k != "id"}, ensure_ascii=False).encode())


def remove(did: str) -> None:
    with lock:
        try:
            _path(did).unlink()
        except FileNotFoundError:
            raise KeyError(did)


def listing() -> list[dict]:
    rows = []
    if DIRECTORY.exists():
        for path in DIRECTORY.glob("*.json"):
            try:
                record = load(path.stem)
            except KeyError:
                continue
            rows.append({"id": record["id"], "title": record["title"], "created": record["created"], "count": len(record["items"])})
    return sorted(rows, key=lambda r: r["created"], reverse=True)[:MAX_DIORAMAS]


def count() -> int:
    return len(list(DIRECTORY.glob("*.json"))) if DIRECTORY.exists() else 0


def prune_ambient(keep: int = 10) -> None:
    rows = []
    for path in DIRECTORY.glob("*.json") if DIRECTORY.exists() else []:
        try:
            record = load(path.stem)
        except KeyError:
            continue
        if record["ambient"]:
            rows.append(record)
    for stale in sorted(rows, key=lambda r: r["created"], reverse=True)[keep:]:
        try:
            remove(stale["id"])
        except KeyError:
            continue
