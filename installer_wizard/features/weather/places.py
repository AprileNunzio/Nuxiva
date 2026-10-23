import json
import re
import secrets
import threading

from config import STATE_DIR
from sealed import write_private

FILE = STATE_DIR / "weather.json"
MAX_PLACES = 24
ID_RE = re.compile(r"^[0-9a-f]{8}$")
NAME_MAX = 80
lock = threading.RLock()


def _clean(value, limit: int) -> str:
    return re.sub(r"[\x00-\x1f\x7f<>]", "", str(value or "")).strip()[:limit]


def load() -> dict:
    try:
        data = json.loads(FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        data = {}
    rows = data.get("places") if isinstance(data, dict) else []
    places = [p for p in rows if isinstance(p, dict) and ID_RE.fullmatch(str(p.get("id", ""))) and _valid(p)] if isinstance(rows, list) else []
    default = data.get("default") if isinstance(data, dict) else ""
    return {"places": places, "default": default if any(p["id"] == default for p in places) else ""}


def _valid(place: dict) -> bool:
    try:
        return -90 <= float(place["lat"]) <= 90 and -180 <= float(place["lon"]) <= 180 and bool(place.get("name"))
    except (KeyError, TypeError, ValueError):
        return False


def _save(data: dict) -> None:
    FILE.parent.mkdir(parents=True, exist_ok=True)
    write_private(FILE, json.dumps(data, ensure_ascii=False).encode())


def add(name: str, lat, lon, detail: str = "", make_default: bool = False) -> dict:
    place = {"id": secrets.token_hex(4), "name": _clean(name, NAME_MAX), "detail": _clean(detail, 90),
             "lat": round(float(lat), 4), "lon": round(float(lon), 4)}
    if not _valid(place):
        raise ValueError("località non valida")
    with lock:
        data = load()
        if len(data["places"]) >= MAX_PLACES:
            raise ValueError("numero massimo di località raggiunto")
        twin = next((p for p in data["places"] if abs(p["lat"] - place["lat"]) < 0.02 and abs(p["lon"] - place["lon"]) < 0.02), None)
        if twin:
            place = twin
        else:
            data["places"].append(place)
        if make_default or not data["default"]:
            data["default"] = place["id"]
        _save(data)
    return place


def remove(place_id: str) -> bool:
    with lock:
        data = load()
        kept = [p for p in data["places"] if p["id"] != place_id]
        if len(kept) == len(data["places"]):
            return False
        data["places"] = kept
        if data["default"] == place_id:
            data["default"] = kept[0]["id"] if kept else ""
        _save(data)
    return True


def set_default(place_id: str) -> bool:
    with lock:
        data = load()
        if not any(p["id"] == place_id for p in data["places"]):
            return False
        data["default"] = place_id
        _save(data)
    return True


def rename(place_id: str, name: str) -> bool:
    label = _clean(name, NAME_MAX)
    if not label:
        return False
    with lock:
        data = load()
        target = next((p for p in data["places"] if p["id"] == place_id), None)
        if target is None:
            return False
        target["name"] = label
        _save(data)
    return True


def find(place_id: str) -> dict | None:
    return next((p for p in load()["places"] if p["id"] == place_id), None)


def default() -> dict | None:
    data = load()
    return next((p for p in data["places"] if p["id"] == data["default"]), None)
