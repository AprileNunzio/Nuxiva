import re
import secrets

from features.diorama.catalog import BY_ID, LENS_DEFAULT, LENSES, LIGHT_DEFAULT, LIGHTS

HEX = re.compile(r"^#[0-9a-fA-F]{6}$")
ID_RE = re.compile(r"^[0-9a-f]{8}$")
TEXT_STRIP = re.compile(r"[^A-Za-z0-9 .,:!?\-+/&()À-ſ]")
MAX_ITEMS = 500
MOVERS = frozenset({"train", "person", "car"})
BASE_LIMITS = {"w": (4.0, 40.0, 22.0), "d": (4.0, 40.0, 15.0), "depth": (0.2, 3.0, 1.2)}
COORD = 40.0


class SpecError(ValueError):
    pass


def _number(value, low: float, high: float, default: float) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    if number != number or number in (float("inf"), float("-inf")):
        return default
    return round(max(low, min(high, number)), 3)


def clean_text(value, limit: int) -> str:
    return TEXT_STRIP.sub("", str(value or ""))[:limit].strip()


def new_id() -> str:
    return secrets.token_hex(4)


def clean_params(kind: str, raw) -> dict:
    definition = BY_ID[kind].params
    source = raw if isinstance(raw, dict) else {}
    out = {}
    for name, p in definition.items():
        value = source.get(name, p.default)
        if p.kind == "number":
            out[name] = _number(value, p.low, p.high, float(p.default))
        elif p.kind == "color":
            out[name] = value if isinstance(value, str) and HEX.fullmatch(value) else p.default
        elif p.kind == "choice":
            out[name] = value if value in p.choices else p.default
        elif p.kind == "flag":
            out[name] = bool(value) if isinstance(value, (bool, int)) else bool(p.default)
        else:
            out[name] = clean_text(value, int(p.high)) or p.default
    return out


def clean_motion(raw) -> dict:
    if not isinstance(raw, dict):
        return {}
    speed = _number(raw.get("speed"), -4.0, 4.0, 0.0)
    if abs(speed) < 0.05:
        return {}
    return {"axis": "z" if raw.get("axis") == "z" else "x", "speed": speed, "span": _number(raw.get("span"), 4.0, 60.0, 24.0)}


def clean_item(raw, existing_id: str = "") -> dict:
    if not isinstance(raw, dict):
        raise SpecError("item_invalid")
    kind = raw.get("kind")
    if kind not in BY_ID:
        raise SpecError("kind_unknown")
    return {
        "id": existing_id or (raw.get("id") if ID_RE.fullmatch(str(raw.get("id", ""))) else new_id()),
        "kind": kind,
        "x": _number(raw.get("x"), -COORD, COORD, 0.0),
        "y": _number(raw.get("y"), -5.0, 20.0, 0.0),
        "z": _number(raw.get("z"), -COORD, COORD, 0.0),
        "rot": _number(raw.get("rot"), -360.0, 360.0, 0.0),
        "scale": _number(raw.get("scale"), 0.1, 5.0, 1.0),
        "params": clean_params(kind, raw.get("params")),
        "motion": clean_motion(raw.get("motion")) if kind in MOVERS else {},
    }


def clean_base(raw) -> dict:
    source = raw if isinstance(raw, dict) else {}
    base = {name: _number(source.get(name), low, high, default) for name, (low, high, default) in BASE_LIMITS.items()}
    soil = source.get("soil")
    top = source.get("top")
    base["soil"] = soil if isinstance(soil, str) and HEX.fullmatch(soil) else "#6b4a2f"
    base["top"] = top if isinstance(top, str) and HEX.fullmatch(top) else "#7da04a"
    return base


def clean_look(raw) -> dict:
    source = raw if isinstance(raw, dict) else {}
    light = source.get("light")
    lens = source.get("lens")
    return {"light": light if light in LIGHTS else LIGHT_DEFAULT, "lens": lens if lens in LENSES else LENS_DEFAULT,
            "blur": _number(source.get("blur"), 0.0, 1.0, 0.6), "mist": _number(source.get("mist"), 0.0, 1.0, 0.25),
            "angle": _number(source.get("angle"), 10.0, 85.0, 38.0), "orbit": bool(source.get("orbit", True))}


def clean_items(rows) -> list[dict]:
    if not isinstance(rows, list):
        return []
    items = []
    for row in rows[:MAX_ITEMS]:
        try:
            items.append(clean_item(row))
        except SpecError:
            continue
    return items


def empty(title: str = "") -> dict:
    return {"title": clean_text(title, 80), "base": clean_base({}), "look": clean_look({}), "items": [], "story": ""}
