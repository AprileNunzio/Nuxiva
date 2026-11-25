import math
import unicodedata

MAX_PARTS = 96
MAX_LAYER = 7
LIMIT = 10_000.0
MIN_HALF = 0.0005
NAME_MAX = 48
INFO_MAX = 240
TITLE_MAX = 64
CORE = 0.05
NEST = 1.5
PALETTE = ("#5ef2ff", "#9b7bff", "#66ffe3", "#ff7be5", "#7aa2ff", "#ffd166")
BANNED = set('<>"`\\')
PARTICLE = {
    "box": ("box", (1, 1, 1), 0.0, False), "cylinder": ("cylinder", (1, 1, 1), 0.0, False),
    "cone": ("cone", (1, 1, 1), 0.0, False), "torus": ("torus", (1, 0.26, 1), 0.26, False),
    "helix": ("helix", (1, 1, 1), 0.05, False), "spiral": ("spiral", (1, 0.04, 1), 0.04, False),
    "plane": ("box", (1, 0.01, 1), 0.0, False), "disc": ("cylinder", (1, 0.06, 1), 0.0, False),
    "ring": ("torus", (1, 0.05, 1), 0.19, False), "orbit": ("torus", (1, 0.02, 1), 0.02, False),
    "cloud": ("sphere", (1, 1, 1), 0.0, True), "halo": ("sphere", (1, 1, 1), 0.0, True),
}
FLOOR_Y = {"spiral": 0.01, "plane": 0.005, "disc": 0.01, "ring": 0.01, "orbit": 0.005}
MOTIONS = ("none", "spin", "pulse", "orbit", "sway")
MODEL = {"box", "wedge", "sphere", "cylinder", "cone", "capsule", "torus", "helix"}


def _num(value, default: float = 0.0) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        return default
    return max(-LIMIT, min(LIMIT, float(value)))


def _vec(value, default: float) -> list[float]:
    if not isinstance(value, (list, tuple)) or len(value) != 3:
        return [default] * 3
    return [_num(v, default) for v in value]


def _text(value, limit: int) -> str:
    if not isinstance(value, str):
        return ""
    kept = "".join(c for c in value if c not in BANNED and unicodedata.category(c)[0] != "C")[:limit]
    return " ".join(kept.split())


def _color(value, index: int) -> str:
    ok = isinstance(value, str) and len(value) == 7 and value.startswith("#") and all(c in "0123456789abcdefABCDEF" for c in value[1:])
    return value.lower() if ok else PALETTE[index % len(PALETTE)]


def _particle(kind: str, size: list[float]) -> tuple[str, list[float], float, bool]:
    shape, k, tube, soft = PARTICLE.get(kind, ("sphere", (1, 1, 1), 0.0, False))
    half = [abs(s) * f for s, f in zip(size, k)]
    if kind in FLOOR_Y:
        half[1] = max(half[1], FLOOR_Y[kind])
    return shape, half, tube, soft


def _model(kind: str, part: dict) -> tuple[str, list[float], float, bool] | None:
    if kind not in MODEL:
        return None
    radii = [abs(_num(part.get(k))) for k in ("radius", "radius_top", "radius_bottom") if k in part]
    r = max([MIN_HALF, *radii])
    h = (abs(_num(part.get("height"), r * 2.0)) if "height" in part else r * 2.0) * 0.5
    size = [abs(v) * 0.5 for v in _vec(part.get("size"), 10.0)]
    if kind in ("box", "wedge"):
        return kind, size, 0.0, False
    if kind == "sphere":
        return kind, [r, r, r], 0.0, False
    if kind == "torus":
        t = max(MIN_HALF, abs(_num(part.get("tube"), r * 0.25))) if "tube" in part else r * 0.25
        outer = r + t
        return kind, [outer, t, outer], max(0.02, min(0.9, t / outer)), False
    if kind == "capsule":
        return kind, [r, max(h, r), r], 0.0, False
    return kind, [r, h, r], 0.05 if kind == "helix" else 0.0, False


def _part(raw: dict, particles: bool, index: int) -> dict | None:
    kind = raw.get("shape")
    if not isinstance(kind, str):
        return None
    found = _particle(kind, _vec(raw.get("size"), 1.0)) if particles else _model(kind, raw)
    if found is None:
        return None
    shape, half, tube, soft = found
    name, label = _text(raw.get("name"), NAME_MAX), _text(raw.get("label"), NAME_MAX)
    layer = raw.get("layer")
    given = isinstance(layer, (int, float)) and not isinstance(layer, bool) and math.isfinite(layer)
    metal_raw = raw.get("metal")
    metal = 0.9 if metal_raw is True else max(0.0, min(1.0, _num(metal_raw, 0.1))) if isinstance(metal_raw, (int, float)) and metal_raw is not False else 0.1
    rough_raw = raw.get("roughness")
    rough = max(0.02, min(1.0, _num(rough_raw))) if isinstance(rough_raw, (int, float)) and not isinstance(rough_raw, bool) else (0.22 if metal > 0.5 else 0.55)
    return {"name": name, "label": label or name, "info": _text(raw.get("info"), INFO_MAX), "shape": shape,
            "half": [max(MIN_HALF, v) for v in half], "tube": tube, "at": _vec(raw.get("at" if particles else "position"), 0.0),
            "rot": [max(-360.0, min(360.0, v)) for v in _vec(raw.get("rot" if particles else "rotation"), 0.0)],
            "color": _color(raw.get("color"), index), "metal": metal, "rough": rough, "soft": soft, "motion": raw.get("motion") if raw.get("motion") in MOTIONS else "none",
            "layer": int(max(0, min(MAX_LAYER, round(layer)))) if given else 0, "explode": [0.0, 0.0, 0.0], "_given": given}


def _reach(part: dict) -> list[float]:
    return [max(part["half"])] * 3 if any(abs(r) > 0.5 for r in part["rot"]) else part["half"]


def _normalize(parts: list[dict]) -> None:
    lo, hi = [math.inf] * 3, [-math.inf] * 3
    for part in parts:
        for axis, span in enumerate(_reach(part)):
            lo[axis] = min(lo[axis], part["at"][axis] - span)
            hi[axis] = max(hi[axis], part["at"][axis] + span)
    center = [(a + b) * 0.5 for a, b in zip(lo, hi)]
    extent = max((b - a) * 0.5 for a, b in zip(lo, hi))
    scale = 1.0 / extent if math.isfinite(extent) and extent > 1e-7 else 1.0
    for part in parts:
        part["at"] = [(a - c) * scale for a, c in zip(part["at"], center)]
        part["half"] = [h * scale for h in part["half"]]


def _volume(part: dict) -> float:
    return part["half"][0] * part["half"][1] * part["half"][2]


def _depth(inner: dict, parts: list[dict]) -> int:
    own = _volume(inner)
    count = sum(1 for outer in parts if outer is not inner and _volume(outer) > own * NEST
                and all(abs(p - c) < s for p, c, s in zip(inner["at"], outer["at"], _reach(outer))))
    return min(MAX_LAYER, count)


def _explode(part: dict) -> list[float]:
    length = math.sqrt(sum(v * v for v in part["at"]))
    if length < CORE:
        return [0.0, 0.0, 0.0]
    push = 0.35 + 0.15 * part["layer"]
    return [v / length * push for v in part["at"]]


def prepare(spec, limit: int = MAX_PARTS) -> dict:
    if not isinstance(spec, dict):
        raise ValueError("holo_bad_json")
    items = spec.get("parts")
    if not isinstance(items, list):
        raise ValueError("holo_no_parts")
    particles = spec.get("source") == "particles"
    parts = [p for p in (_part(raw, particles, i) for i, raw in enumerate(items[:limit]) if isinstance(raw, dict)) if p]
    if not parts:
        raise ValueError("holo_no_parts")
    _normalize(parts)
    if not any(p["_given"] for p in parts):
        depths = [_depth(p, parts) for p in parts]
        for part, depth in zip(parts, depths):
            part["layer"] = depth
    for part in parts:
        part["explode"] = _explode(part)
        del part["_given"]
    return {"title": _text(spec.get("title"), TITLE_MAX), "euler": "ZYX" if particles else "XYZ", "parts": parts,
            "layers": max(p["layer"] for p in parts) + 1, "radius": 1.0}
