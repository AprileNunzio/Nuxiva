import json
import re
import threading

from config import STATE_DIR
from sealed import write_private

from features.diorama import spec as S
from features.diorama.catalog import BY_ID, MATERIALS

FILE = STATE_DIR / "diorama" / "learned.json"
MAX_LEARNED = 60
MAX_PARTS = 48
SHAPES = ("box", "cylinder", "cone", "sphere")
ID_RE = re.compile(r"^x_[a-z0-9_]{2,30}$")
lock = threading.RLock()


def _num(value, low: float, high: float, default: float) -> float:
    return S._number(value, low, high, default)


def _part(raw) -> dict | None:
    if not isinstance(raw, dict) or raw.get("shape") not in SHAPES:
        return None
    color = raw.get("color")
    return {
        "shape": raw["shape"], "x": _num(raw.get("x"), -8, 8, 0), "y": _num(raw.get("y"), 0, 12, 0), "z": _num(raw.get("z"), -8, 8, 0),
        "w": _num(raw.get("w"), 0.02, 12, 0.3), "h": _num(raw.get("h"), 0.02, 12, 0.3), "d": _num(raw.get("d"), 0.02, 12, 0.3),
        "r": _num(raw.get("r"), 0.01, 6, 0.15), "r2": _num(raw.get("r2"), 0.0, 6, 0.15), "rot": _num(raw.get("rot"), -360, 360, 0),
        "material": raw.get("material") if raw.get("material") in MATERIALS else "paint",
        "color": color if isinstance(color, str) and S.HEX.fullmatch(color) else "#b0b0b0", "tint": raw.get("tint") is True,
    }


def clean_recipe(raw) -> dict | None:
    source = raw if isinstance(raw, dict) else {}
    parts = [p for p in (_part(x) for x in (source.get("parts") if isinstance(source.get("parts"), list) else [])[:MAX_PARTS]) if p]
    if len(parts) < 3:
        return None
    return {"parts": parts, "mover": source.get("mover") is True}


def slug(label: str) -> str:
    base = re.sub(r"[^a-z0-9]+", "_", S.clean_text(label, 40).lower()).strip("_")[:28]
    return f"x_{base}" if len(base) >= 2 else ""


_cache: tuple[tuple[str, int], dict[str, dict]] = (('', -1), {})


def load() -> dict[str, dict]:
    global _cache
    try:
        stamp = FILE.stat().st_mtime_ns
    except OSError:
        return {}
    key = (str(FILE), stamp)
    if key == _cache[0]:
        return _cache[1]
    try:
        data = json.loads(FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    result = _parse(data)
    _cache = (key, result)
    return result


def _parse(data) -> dict[str, dict]:
    out = {}
    for kind, row in (data.items() if isinstance(data, dict) else []):
        recipe = clean_recipe(row.get("recipe")) if isinstance(row, dict) else None
        if ID_RE.fullmatch(kind) and kind not in BY_ID and recipe:
            out[kind] = {"label": S.clean_text(row.get("label"), 40) or kind, "hint": S.clean_text(row.get("hint"), 120), "recipe": recipe,
                         "created": int(row.get("created") or 0)}
    return out


def add(label: str, hint: str, raw_recipe, created: int) -> str | None:
    kind, recipe = slug(label), clean_recipe(raw_recipe)
    if not kind or recipe is None or kind in BY_ID:
        return None
    with lock:
        data = dict(load())
        if kind in data or len(data) >= MAX_LEARNED:
            return None
        data[kind] = {"label": S.clean_text(label, 40), "hint": S.clean_text(hint, 120), "recipe": recipe, "created": created}
        FILE.parent.mkdir(parents=True, exist_ok=True)
        write_private(FILE, json.dumps(data, ensure_ascii=False).encode())
    return kind


def remove(kind: str) -> bool:
    with lock:
        data = dict(load())
        if kind not in data:
            return False
        del data[kind]
        write_private(FILE, json.dumps(data, ensure_ascii=False).encode())
    return True


def recipes_for(kinds: set[str]) -> dict[str, dict]:
    return {k: v["recipe"] for k, v in load().items() if k in kinds}
