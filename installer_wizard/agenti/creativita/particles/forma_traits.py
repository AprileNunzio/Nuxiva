import json
import math
import os

from agenti.particles.forma import FormaError, compile_plan

DEFAULTS = {"symmetry": "radial", "body": "sphere", "length": 1.5, "width": 1.0, "limb": "spread", "limbs": 4,
            "limb_length": 1.0, "curl": 0.0, "rings": 0, "theme": "ethereal"}
SCHEMA = {"fields": [
    {"name": "symmetry", "kind": "string", "required": True, "values": ["radial", "bilateral", "axial", "spiral", "orbital"]},
    {"name": "body", "kind": "string", "required": True, "values": ["dome", "bell", "spindle", "sphere", "column", "disc", "cone"]},
    {"name": "length", "kind": "number", "required": True, "range": [0.2, 4.0]},
    {"name": "width", "kind": "number", "required": True, "range": [0.1, 3.0]},
    {"name": "limb", "kind": "string", "required": False, "values": ["hang", "spread", "reach", "spoke", "wing"]},
    {"name": "limbs", "kind": "number", "required": False, "range": [0, 24]},
    {"name": "limb_length", "kind": "number", "required": False, "range": [0.1, 4.0]},
    {"name": "curl", "kind": "number", "required": False, "range": [-2.0, 2.0]},
    {"name": "rings", "kind": "number", "required": False, "range": [0, 6]},
    {"name": "theme", "kind": "string", "required": False,
     "values": ["bioluminescent", "celestial", "botanical", "fauna", "mechanical", "microscopic", "geological", "ethereal"]},
]}
SAMPLES = 8


def _native():
    if os.environ.get("NUXIVA_NATIVE", "auto").strip() == "0":
        return None
    try:
        import nuxiva_native
    except ImportError:
        return None
    return nuxiva_native if hasattr(nuxiva_native, "forma_sculpt") else None


def _clean(value, lo: float, hi: float, fallback: float) -> float:
    return max(lo, min(hi, float(value))) if isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) else fallback


def _whole(value, hi: int, fallback: int) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
        return fallback
    return min(hi, int(value))


def _profile(body: str, length: float, width: float) -> list[list[float]]:
    rows = []
    for i in range(SAMPLES):
        t = i / (SAMPLES - 1)
        y = length * (t - 0.5)
        if body == "dome":
            r = width * math.sqrt(max(0.0, 1.0 - t * t))
        elif body == "bell":
            r = width * math.sqrt(max(0.0, 1.0 - t ** 1.6))
        elif body == "spindle":
            r = width * math.sin(math.pi * (0.08 + 0.84 * t))
        elif body == "column":
            r = width * (1.0 - 0.15 * t)
        elif body == "disc":
            r, y = width * math.sqrt(max(0.0, 1.0 - t * t)), length * 0.2 * (t - 0.5)
        elif body == "cone":
            r = width * (1.0 - t)
        else:
            r = width * math.sin(math.pi * (0.05 + 0.9 * t))
        rows.append([max(0.0, r), y])
    return rows


def _lathe(body: str, length: float, width: float) -> dict:
    return {"op": "lathe", "profile": _profile(body, length, width), "color": 0, "weight": 2.0}


def _path(curl: float, hanging: bool) -> str:
    return "line" if abs(curl) < 0.05 else ("wave" if hanging else "arc")


def _radial(t: dict, length: float, width: float, reach: float, curl: float):
    if t["limbs"] == 0:
        return None
    base, heading, rim = {"hang": (-length * 0.5, [0.0, -1.0, 0.0], width * 0.8), "reach": (length * 0.5, [0.35, 1.0, 0.0], width * 0.8),
                          "spoke": (0.0, [1.0, 0.0, 0.0], 0.0)}.get(t["limb"], (0.0, [1.0, -0.15, 0.0], width * 0.8))
    steps = min(5, max(2, 56 // max(1, t["limbs"])))
    return {"op": "radial", "count": t["limbs"], "radius": rim, "phase": 0.0, "child": {
        "op": "sweep", "path": _path(curl, t["limb"] == "hang"), "from": [0.0, base, 0.0], "dir": heading, "length": reach, "bend": curl,
        "r0": width * 0.06, "r1": width * 0.015, "steps": steps, "color": 2, "weight": 1.0}}


def _bilateral(t: dict, length: float, width: float, reach: float, curl: float) -> list[dict]:
    nodes = [{"op": "rotate", "axis": "x", "deg": 90.0, "child": _lathe(t["body"], length, width)}]
    pairs = max(t["limbs"] // 2, 1 if t["limbs"] > 0 else 0)
    heading, r0, r1 = ([0.3, -1.0, 0.0], width * 0.12, width * 0.05) if t["limb"] == "hang" else ([1.0, 0.1, -0.3], width * 0.22, width * 0.05)
    steps = min(4, max(1, 72 // max(1, pairs * 2)))
    for k in range(pairs):
        spread = k / (pairs - 1) - 0.5 if pairs > 1 else 0.0
        nodes.append({"op": "mirror", "axis": "x", "child": {
            "op": "sweep", "path": _path(curl, False), "from": [width * 0.5, 0.0, -spread * length * 0.6], "dir": heading, "length": reach,
            "bend": curl, "r0": r0, "r1": r1, "steps": steps, "color": 3, "weight": 1.2}})
    nodes.append({"op": "sweep", "path": "line", "from": [0.0, 0.0, -length * 0.5], "dir": [0.0, 0.0, -1.0], "length": reach * 0.5,
                  "bend": 0.0, "r0": width * 0.2, "r1": width * 0.03, "steps": 3, "color": 2, "weight": 0.8})
    return nodes


def _orbital(t: dict, width: float) -> list[dict]:
    nodes = [{"op": "blob", "shape": "sphere", "at": [0.0, 0.0, 0.0], "size": [width * 0.8] * 3, "rot": [0.0, 0.0, 0.0], "color": 0, "weight": 2.6}]
    rings = max(t["rings"], 2)
    for i in range(rings):
        f = i / rings
        radius = width * (1.3 + 0.45 * i)
        nodes.append({"op": "blob", "shape": "torus", "at": [0.0, 0.0, 0.0], "size": [radius, radius * 0.14, radius],
                      "rot": [25.0 + f * 40.0, 0.0, -15.0 + f * 55.0], "color": i + 1, "weight": 1.5})
        theta = f * math.tau + 0.5
        nodes.append({"op": "blob", "shape": "sphere", "at": [radius * math.cos(theta) * 0.85, radius * math.sin(theta) * 0.4,
                                                              radius * math.sin(theta * 1.2) * 0.75],
                      "size": [width * 0.15] * 3, "rot": [0.0, 0.0, 0.0], "color": i + 3, "weight": 0.9})
    return nodes


def _spiral(length: float, width: float) -> list[dict]:
    return [{"op": "radial", "count": 2, "radius": 0.0, "phase": 0.0, "child": {
        "op": "sweep", "path": "spiral", "from": [0.0, -length * 0.5, 0.0], "dir": [0.0, 1.0, 0.0], "length": length,
        "bend": min(2.0, width / (length * 0.3)), "r0": width * 0.12, "r1": width * 0.12, "steps": 12, "color": 1, "weight": 1.5}},
        {"op": "blob", "shape": "sphere", "at": [0.0, 0.0, 0.0], "size": [width * 0.25] * 3, "rot": [0.0, 0.0, 0.0], "color": 0, "weight": 1.2}]


def normalize(raw) -> dict:
    if not isinstance(raw, dict) or set(raw) - set(DEFAULTS):
        raise FormaError("bad_traits")
    t = {**DEFAULTS, **raw}
    for key in ("symmetry", "body", "limb", "theme"):
        if not isinstance(t[key], str):
            raise FormaError("bad_traits")
    t["length"] = _clean(t["length"], 0.2, 4.0, 1.5)
    t["width"] = _clean(t["width"], 0.1, 3.0, 1.0)
    t["limb_length"] = _clean(t["limb_length"], 0.1, 4.0, 1.0)
    t["curl"] = _clean(t["curl"], -2.0, 2.0, 0.0)
    t["limbs"] = _whole(t["limbs"], 24, 4)
    t["rings"] = _whole(t["rings"], 6, 0)
    return t


def compose(raw) -> dict:
    t = normalize(raw)
    length, width, reach, curl = t["length"], t["width"], t["limb_length"], t["curl"]
    if t["symmetry"] == "orbital":
        nodes = _orbital(t, width)
    elif t["symmetry"] == "spiral":
        nodes = _spiral(length, width)
    elif t["symmetry"] == "bilateral":
        nodes = _bilateral(t, length, width, reach, curl)
    elif t["symmetry"] == "axial":
        nodes = [_lathe(t["body"], length, width)]
        for k in range(t["rings"]):
            nodes.append({"op": "blob", "shape": "torus", "at": [0.0, (k / max(1, t["rings"]) - 0.5) * length, 0.0],
                          "size": [width * 1.2, width * 0.2, width * 1.2], "rot": [0.0, 0.0, 0.0], "color": k + 1, "weight": 1.2})
    else:
        nodes = [_lathe(t["body"], length, width)]
        limbs = _radial(t, length, width, reach, curl)
        if limbs:
            nodes.append(limbs)
    return {"theme": t["theme"], "nodes": nodes}


def sculpt(raw) -> dict:
    lib = _native()
    if lib is not None:
        try:
            return json.loads(lib.forma_sculpt(json.dumps(normalize_for_native(raw), ensure_ascii=False)))
        except ValueError as exc:
            raise FormaError(str(exc)) from exc
    return compile_plan(compose(raw))


def normalize_for_native(raw) -> dict:
    if not isinstance(raw, dict) or set(raw) - set(DEFAULTS):
        raise FormaError("bad_traits")
    out = dict(raw)
    for key in ("limbs", "rings"):
        if key in out:
            out[key] = _whole(out[key], 24, 0)
    for key in ("length", "width", "limb_length", "curl"):
        if key in out and not (isinstance(out[key], (int, float)) and not isinstance(out[key], bool) and math.isfinite(out[key])):
            del out[key]
    return out
