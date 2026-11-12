import json
import math
import os

from agenti.particles.forma import FormaError, compile_plan
from agenti.particles.forma_anatomy import (PRESETS, _clean, _matches, _words, blob, curve, group, mark, seg)

DEFAULTS = {"kind": "planet", "size": 1.0, "tilt": 20.0, "arms": 2, "rings": 0, "moons": 0, "planets": 5, "bands": 0, "glow": 1.0, "theme": "celestial"}
SCHEMA = {"fields": [
    {"name": "kind", "kind": "string", "required": True, "values": ["galaxy", "star", "planet", "nebula", "blackhole", "system"]},
    {"name": "size", "kind": "number", "required": True, "range": [0.3, 3.0]},
    {"name": "tilt", "kind": "number", "required": False, "range": [-90.0, 90.0]},
    {"name": "arms", "kind": "number", "required": False, "range": [1, 6]},
    {"name": "rings", "kind": "number", "required": False, "range": [0, 4]},
    {"name": "moons", "kind": "number", "required": False, "range": [0, 4]},
    {"name": "planets", "kind": "number", "required": False, "range": [1, 8]},
    {"name": "bands", "kind": "number", "required": False, "range": [0, 8]},
    {"name": "glow", "kind": "number", "required": False, "range": [0.3, 2.5]},
    {"name": "theme", "kind": "string", "required": False,
     "values": ["bioluminescent", "celestial", "botanical", "fauna", "mechanical", "microscopic", "geological", "ethereal"]},
]}
LIMITS = {"size": (0.3, 3.0), "tilt": (-90.0, 90.0), "glow": (0.3, 2.5)}
WHOLE = {"arms": 6, "rings": 4, "moons": 4, "planets": 8, "bands": 8}
PRESET_FILE = PRESETS.with_name("cosmos_presets.json")


def _native():
    if os.environ.get("NUXIVA_NATIVE", "auto").strip() == "0":
        return None
    try:
        import nuxiva_native
    except ImportError:
        return None
    return nuxiva_native if hasattr(nuxiva_native, "forma_cosmos_sculpt") else None


def _whole(value, hi: int, fallback: int) -> int:
    ok = isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) and value >= 0
    return min(hi, int(value)) if ok else fallback


def normalize(raw) -> dict:
    if not isinstance(raw, dict) or set(raw) - set(DEFAULTS):
        raise FormaError("bad_cosmos")
    t = {**DEFAULTS, **raw}
    for key in ("kind", "theme"):
        if not isinstance(t[key], str):
            raise FormaError("bad_cosmos")
    for key, (lo, hi) in LIMITS.items():
        t[key] = _clean(t[key], lo, hi, DEFAULTS[key])
    for key, hi in WHOLE.items():
        t[key] = _whole(t[key], hi, DEFAULTS[key])
    return t


def _ball(shape, at, size, color, weight) -> dict:
    return blob(shape, at, size, color, weight)


def galaxy(c) -> list[dict]:
    s = c["size"]
    return [_ball("cloud", [0.0] * 3, [0.28 * s, 0.2 * s, 0.28 * s], 0, 3.0), _ball("disc", [0.0] * 3, [s] * 3, 4, 1.6),
            {"op": "radial", "count": max(1, min(6, c["arms"])), "radius": 0.0, "phase": 0.0, "child": _ball("spiral", [0.0] * 3, [s] * 3, 1, 2.2)},
            _ball("halo", [0.0] * 3, [1.15 * s] * 3, 2, 0.5), mark("bulge", [0.0, 0.1 * s, 0.0]), mark("arms", [0.6 * s, 0.0, 0.35 * s]),
            mark("disk", [0.8 * s, 0.0, -0.2 * s]), mark("halo", [0.0, 0.9 * s, 0.0])]


def star(c) -> list[dict]:
    s, g = c["size"], c["glow"]
    return [_ball("sphere", [0.0] * 3, [s] * 3, 5, 3.0), _ball("halo", [0.0] * 3, [1.5 * s * g] * 3, 0, 2.0 * g),
            {"op": "radial", "count": 6, "radius": 0.0, "phase": 0.0,
             "child": curve([s, 0.0, 0.0], [1.0, 0.4, 0.0], 0.6 * s, 0.8, 0.12 * s, 0.01 * s, 3, 0)},
            mark("surface", [0.0, s, 0.0]), mark("corona", [1.2 * s * g, 0.6 * s, 0.0]), mark("flares", [1.4 * s, 0.2 * s, 0.0])]


def planet(c) -> list[dict]:
    s = c["size"]
    body = [_ball("sphere", [0.0] * 3, [s] * 3, 1, 5.0), _ball("halo", [0.0] * 3, [1.12 * s] * 3, 4, 0.5),
            mark("surface", [0.7 * s, 0.7 * s, 0.0]), mark("atmosphere", [1.1 * s, 0.3 * s, 0.0])]
    bands = c["bands"]
    for i in range(bands):
        lat = -0.6 + 1.2 * i / (bands - 1) if bands > 1 else 0.0
        flat = math.sqrt(max(0.0, 1.0 - lat * lat))
        body.append(_ball("orbit", [0.0, s * lat, 0.0], [s * flat * 1.01, 0.02 * s, s * flat * 1.01], i % 2 * 2, 2.0))
    if bands > 0:
        body.append(mark("bands", [0.0, 0.3 * s, s * 0.95]))
    for i in range(c["rings"]):
        body.append(_ball("ring", [0.0] * 3, [s * (1.35 + 0.4 * i)] * 3, i % 3 + 2, 0.7))
    if c["rings"] > 0:
        body.append(mark("rings", [1.8 * s, 0.0, 0.0]))
    out = [{"op": "rotate", "axis": "x", "deg": c["tilt"], "child": group(body)}]
    for j in range(c["moons"]):
        angle, dist = j * 2.4, s * (2.2 + 0.7 * j)
        out.append(_ball("sphere", [dist * math.cos(angle), 0.1 * s * math.sin(angle), dist * math.sin(angle)], [0.12 * s] * 3, 0, 10.0))
    if c["moons"] > 0:
        out.append(mark("moons", [2.2 * s, 0.2 * s, 0.0]))
    return out


def nebula(c) -> list[dict]:
    s = c["size"]
    return [_ball("cloud", [0.0] * 3, [0.7 * s, 0.5 * s, 0.6 * s], 3, 2.0),
            {"op": "radial", "count": 5, "radius": 0.45 * s, "phase": 20.0, "child": _ball("cloud", [0.0] * 3, [0.55 * s, 0.4 * s, 0.5 * s], 4, 1.6)},
            {"op": "radial", "count": 12, "radius": 0.8 * s, "phase": 7.0, "child": _ball("sphere", [0.0] * 3, [0.03 * s] * 3, 0, 8.0)},
            mark("cloud", [0.4 * s, 0.2 * s, 0.0]), mark("stars", [0.8 * s, 0.0, 0.0])]


def blackhole(c) -> list[dict]:
    s = c["size"]
    return [_ball("sphere", [0.0] * 3, [0.3 * s] * 3, 2, 4.0), _ball("disc", [0.0] * 3, [1.7 * s] * 3, 5, 3.0), _ball("ring", [0.0] * 3, [s] * 3, 0, 3.0),
            {"op": "mirror", "axis": "y", "child": seg([0.0, 0.3 * s, 0.0], [0.0, 2.0 * s, 0.0], 0.08 * s, 0.01 * s, 1, 1.5)},
            mark("horizon", [0.3 * s, 0.1 * s, 0.0]), mark("accretion", [1.2 * s, 0.0, 0.0]), mark("jets", [0.0, 1.6 * s, 0.0])]


def system(c) -> list[dict]:
    s, n = c["size"], max(1, min(8, c["planets"]))
    out = [_ball("sphere", [0.0] * 3, [0.22 * s] * 3, 0, 4.0), _ball("halo", [0.0] * 3, [0.4 * s * c["glow"]] * 3, 5, 2.0),
           mark("star", [0.2 * s, 0.1 * s, 0.0])]
    for i in range(n):
        r, angle = s * (0.3 + 0.7 * (i + 1) / n), i * 2.4
        out.append(_ball("orbit", [0.0] * 3, [r, 0.02 * s, r], 2, 1.0))
        out.append(_ball("sphere", [r * math.cos(angle), 0.0, r * math.sin(angle)], [0.035 * s * (1.0 + 0.5 * (i * 7 % 3))] * 3, i % 5 + 1, 10.0))
        if i == 0:
            out.append(mark("planets", [r * math.cos(angle), 0.05 * s, r * math.sin(angle)]))
            out.append(mark("orbits", [r, 0.0, 0.0]))
    return out


BUILDERS = {"galaxy": galaxy, "star": star, "nebula": nebula, "blackhole": blackhole, "system": system}
TILTED = ("galaxy", "blackhole", "system")


def compose(raw) -> dict:
    c = normalize(raw)
    nodes = BUILDERS.get(c["kind"], planet)(c)
    if c["kind"] in TILTED:
        nodes = [{"op": "rotate", "axis": "x", "deg": c["tilt"], "child": group(nodes)}]
    return {"theme": c["theme"], "nodes": nodes}


def normalize_for_native(raw) -> dict:
    if not isinstance(raw, dict) or set(raw) - set(DEFAULTS):
        raise FormaError("bad_cosmos")
    out = dict(raw)
    for key in LIMITS:
        if key in out and not (isinstance(out[key], (int, float)) and not isinstance(out[key], bool) and math.isfinite(out[key])):
            del out[key]
    for key, hi in WHOLE.items():
        if key in out:
            out[key] = _whole(out[key], hi, DEFAULTS[key])
    return out


def sculpt(raw) -> dict:
    lib = _native()
    if lib is not None:
        try:
            return json.loads(lib.forma_cosmos_sculpt(json.dumps(normalize_for_native(raw), ensure_ascii=False)))
        except ValueError as exc:
            raise FormaError(str(exc)) from exc
    return compile_plan(compose(raw))


def preset(concept: str) -> dict | None:
    lib = _native()
    if lib is not None:
        found = lib.forma_cosmos_preset(str(concept)[:256])
        return json.loads(found) if found else None
    tokens = _words(concept)
    for entry in json.loads(PRESET_FILE.read_text(encoding="utf-8")):
        if any(_matches(t, r) for t in tokens for r in entry["roots"]):
            return {**DEFAULTS, **entry["cosmos"]}
    return None
