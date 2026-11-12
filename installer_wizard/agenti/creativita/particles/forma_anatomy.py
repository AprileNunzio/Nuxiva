import json
import math
import os
from pathlib import Path

from agenti.particles.forma import FormaError, compile_plan

DEFAULTS = {"plan": "quadruped", "size": 1.6, "build": 1.0, "neck": 0.5, "head": 1.0, "snout": 0.5, "ears": "point", "ear_size": 1.0,
            "horns": 0.0, "tail": 1.0, "tail_curl": 0.4, "legs": 1.0, "leg_thick": 1.0, "arms": 1.0, "wings": 0.0, "pairs": 3,
            "theme": "fauna"}
SCHEMA = {"fields": [
    {"name": "plan", "kind": "string", "required": True, "values": ["quadruped", "biped", "bird", "fish", "insect", "serpent"]},
    {"name": "size", "kind": "number", "required": True, "range": [0.4, 4.0]},
    {"name": "build", "kind": "number", "required": False, "range": [0.3, 2.0]},
    {"name": "neck", "kind": "number", "required": False, "range": [0.0, 2.5]},
    {"name": "head", "kind": "number", "required": False, "range": [0.2, 2.0]},
    {"name": "snout", "kind": "number", "required": False, "range": [0.0, 2.5]},
    {"name": "ears", "kind": "string", "required": False, "values": ["none", "point", "round", "floppy", "long"]},
    {"name": "ear_size", "kind": "number", "required": False, "range": [0.2, 2.5]},
    {"name": "horns", "kind": "number", "required": False, "range": [0.0, 2.5]},
    {"name": "tail", "kind": "number", "required": False, "range": [0.0, 3.0]},
    {"name": "tail_curl", "kind": "number", "required": False, "range": [-2.0, 2.0]},
    {"name": "legs", "kind": "number", "required": False, "range": [0.2, 2.5]},
    {"name": "leg_thick", "kind": "number", "required": False, "range": [0.3, 2.5]},
    {"name": "arms", "kind": "number", "required": False, "range": [0.2, 2.5]},
    {"name": "wings", "kind": "number", "required": False, "range": [0.0, 3.0]},
    {"name": "pairs", "kind": "number", "required": False, "range": [1, 6]},
    {"name": "theme", "kind": "string", "required": False,
     "values": ["bioluminescent", "celestial", "botanical", "fauna", "mechanical", "microscopic", "geological", "ethereal"]},
]}
LIMITS = {"size": (0.4, 4.0), "build": (0.3, 2.0), "neck": (0.0, 2.5), "head": (0.2, 2.0), "snout": (0.0, 2.5), "ear_size": (0.2, 2.5),
          "horns": (0.0, 2.5), "tail": (0.0, 3.0), "tail_curl": (-2.0, 2.0), "legs": (0.2, 2.5), "leg_thick": (0.3, 2.5),
          "arms": (0.2, 2.5), "wings": (0.0, 3.0)}
PRESETS = Path(__file__).resolve().parent / "algorithms" / "anatomy_presets.json"
MAX_CONCEPT = 256


def _native():
    if os.environ.get("NUXIVA_NATIVE", "auto").strip() == "0":
        return None
    try:
        import nuxiva_native
    except ImportError:
        return None
    return nuxiva_native if hasattr(nuxiva_native, "forma_anatomy_sculpt") else None


def _clean(value, lo: float, hi: float, fallback: float) -> float:
    ok = isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)
    return max(lo, min(hi, float(value))) if ok else fallback


def normalize(raw) -> dict:
    if not isinstance(raw, dict) or set(raw) - set(DEFAULTS):
        raise FormaError("bad_anatomy")
    t = {**DEFAULTS, **raw}
    for key in ("plan", "ears", "theme"):
        if not isinstance(t[key], str):
            raise FormaError("bad_anatomy")
    for key, (lo, hi) in LIMITS.items():
        t[key] = _clean(t[key], lo, hi, DEFAULTS[key])
    pairs = t["pairs"]
    t["pairs"] = min(6, int(pairs)) if isinstance(pairs, (int, float)) and not isinstance(pairs, bool) and math.isfinite(pairs) and pairs >= 0 else 3
    return t


def seg(a, b, r0, r1, color, weight) -> dict:
    d = [b[0] - a[0], b[1] - a[1], b[2] - a[2]]
    length = max(1e-3, math.sqrt(sum(v * v for v in d)))
    return {"op": "sweep", "path": "line", "from": list(a), "dir": d, "length": length, "bend": 0.0, "r0": r0, "r1": r1, "steps": 1,
            "color": color, "weight": weight}


def curve(origin, heading, length, bend, r0, r1, steps, color) -> dict:
    return {"op": "sweep", "path": "arc", "from": list(origin), "dir": list(heading), "length": max(1e-3, length), "bend": bend, "r0": r0,
            "r1": r1, "steps": steps, "color": color, "weight": 1.2}


def blob(shape, at, size, color, weight, rot=(0.0, 0.0, 0.0)) -> dict:
    return {"op": "blob", "shape": shape, "at": list(at), "size": list(size), "rot": list(rot), "color": color, "weight": weight}


def mark(name, at) -> dict:
    return {"op": "mark", "name": name, "at": list(at)}


def mir(child) -> dict:
    return {"op": "mirror", "axis": "x", "child": child}


def group(children) -> dict:
    return {"op": "group", "children": children}


def lying(profile, weight) -> dict:
    return {"op": "rotate", "axis": "x", "deg": 90.0, "child": {"op": "lathe", "profile": profile, "color": 0, "weight": weight}}


def body_profile(length, radius, front):
    rows = []
    for i in range(15):
        t = i / 14.0
        swell = math.sin(math.pi * (0.07 + 0.86 * t)) ** 0.7
        rows.append([radius * swell * (1.0 + front * (t - 0.5)), length * (t - 0.5)])
    return rows


def limb(hip, knee, foot, t) -> dict:
    fx, fy, fz = foot
    return group([seg(hip, knee, t * 1.25, t * 0.85, 0, 1.3), seg(knee, foot, t * 0.8, t * 0.55, 0, 1.2),
                  blob("sphere", [fx, fy - t * 0.2, fz + t * 0.3], [t * 0.7, t * 0.45, t * 0.95], 1, 1.4)])


def ear(p, hs, c):
    x, y, z = c
    es = p["ears"]
    side = [x + hs * 0.5, y + hs * 0.7, z - hs * 0.1]
    e = p["ear_size"]
    if es == "point":
        node = blob("cone", [side[0], side[1] + hs * 0.3 * e, side[2]], [hs * 0.34 * e, hs * 0.75 * e, hs * 0.14], 1, 1.2)
    elif es == "round":
        node = blob("sphere", side, [hs * 0.34 * e, hs * 0.38 * e, hs * 0.1], 1, 1.4)
    elif es == "floppy":
        node = curve([side[0], side[1] - hs * 0.1, side[2]], [0.6, -0.7, -0.2], hs * 0.95 * e, 0.5, hs * 0.2, hs * 0.13, 2, 1)
    elif es == "long":
        node = curve([x + hs * 0.25, y + hs * 0.7, z - hs * 0.2], [0.2, 1.0, -0.2], hs * 1.7 * e, -0.2, hs * 0.2, hs * 0.07, 2, 1)
    else:
        return None
    return mir(node)


def head(p, hs, c, beak) -> list[dict]:
    x, y, z = c
    out = [blob("sphere", c, [hs * 0.9, hs * 0.85, hs * 1.05], 0, 1.8)]
    if p["snout"] > 0.05:
        end = z + hs * 0.7 + hs * p["snout"] * 1.1
        r0, r1, color = (hs * 0.4, hs * 0.04, 3) if beak else (hs * 0.5, hs * 0.38, 0)
        out.append(seg([x, y - hs * 0.2, z + hs * 0.6], [x, y - hs * 0.3, end], r0, r1, color, 1.3))
        if not beak:
            out.append(blob("sphere", [x, y - hs * 0.28, end + hs * 0.05], [hs * 0.15] * 3, 5, 2.2))
    out.append(mir(blob("sphere", [x + hs * 0.45, y + hs * 0.25, z + hs * 0.5], [hs * 0.13] * 3, 4, 3.0)))
    out.append(mark("head", c))
    out.append(mark("beak" if beak else "snout", [x, y - hs * 0.3, z + hs * 0.7 + hs * p["snout"] * 0.6]))
    if p["ears"] != "none":
        out.append(mark("ears", [x + hs * 0.5, y + hs * 0.9, z - hs * 0.1]))
    found = ear(p, hs, c)
    if found:
        out.append(found)
    if p["horns"] > 0.05:
        out.append(mark("horns", [x + hs * 0.5, y + hs * 1.5, z - hs * 0.2]))
        out.append(mir(curve([x + hs * 0.3, y + hs * 0.7, z - hs * 0.1], [0.5, 1.0, -0.2], hs * p["horns"] * 1.4, 0.7, hs * 0.14, hs * 0.03, 3, 2)))
    return out


def wings(p, root, span) -> list[dict]:
    if p["wings"] < 0.05:
        return []
    thick = span * 0.05
    return [mir(curve(root, d, span * k, -0.3, thick, thick * 0.3, 2, 2))
            for d, k in (([1.0, 0.5, -0.2], 1.0), ([1.0, 0.1, -0.45], 0.9), ([0.8, -0.25, -0.7], 0.7))]


def tail(p, origin, length, radius):
    if p["tail"] <= 0.05:
        return None
    return curve(origin, [0.0, 0.6, -1.0], length * p["tail"], p["tail_curl"], radius, radius * 0.25, 4, 2)


def quadruped(p) -> list[dict]:
    l = p["size"]
    r, h, t = 0.28 * l * p["build"], 0.45 * l * p["legs"], 0.09 * l * p["leg_thick"]
    n = [lying(body_profile(l, r, 0.25), 2.2), mark("body", [0.0, r * 0.2, 0.0]), mark("front_legs", [r * 0.55, -r * 0.1 - h * 0.5, l * 0.3]),
         mark("hind_legs", [r * 0.55, -h * 0.45, -l * 0.3])]
    reach = p["neck"] * l
    base = [0.0, r * 0.45, l * 0.40]
    top = [0.0, r * 0.45 + reach * 0.28, l * 0.40 + reach * 0.22]
    if p["neck"] > 0.05:
        n.append(seg(base, top, r * 0.55, r * 0.4, 0, 1.4))
        n.append(mark("neck", [r * 0.4, r * 0.45 + reach * 0.14, l * 0.4 + reach * 0.11]))
    hs = p["head"] * 0.17 * l
    n.extend(head(p, hs, [top[0], top[1] + hs * 0.15, top[2] + hs * 0.7], False))
    fz, bz = l * 0.32, -l * 0.34
    n.append(mir(limb([r * 0.55, -r * 0.1, fz], [r * 0.55, -r * 0.1 - h * 0.5, fz - l * 0.04], [r * 0.52, -r * 0.1 - h, fz + l * 0.02], t)))
    n.append(mir(limb([r * 0.55, r * 0.05, bz], [r * 0.55, -h * 0.45, bz + l * 0.1], [r * 0.5, -h - r * 0.1, bz - l * 0.06], t)))
    found = tail(p, [0.0, r * 0.35, -l * 0.5], l * 0.45, r * 0.22)
    if found:
        n.append(found)
        ln = l * 0.45 * p["tail"]
        n.append(mark("tail", [0.0, r * 0.35 + ln * 0.3, -l * 0.5 - ln * 0.5]))
    n.extend(wings(p, [r * 0.4, r * 0.8, l * 0.15], p["wings"] * l * 0.7))
    if p["wings"] > 0.05:
        n.append(mark("wings", [r * 0.4 + p["wings"] * l * 0.4, r * 0.8 + p["wings"] * l * 0.2, l * 0.1]))
    return n


def biped(p) -> list[dict]:
    h = p["size"]
    r, t = 0.16 * h * p["build"], 0.045 * h * p["leg_thick"]
    leg, arm = 0.45 * h * p["legs"], 0.38 * h * p["arms"]
    profile = []
    for i in range(8):
        k = i / 7.0
        profile.append([r * (0.78 + 0.22 * math.sin(math.pi * k ** 0.8)), h * (0.2 * k - 0.18 * (1.0 - k))])
    n = [{"op": "lathe", "profile": profile, "color": 0, "weight": 2.2}, mark("body", [0.0, 0.02 * h, r]),
         mark("legs", [r * 0.6, -0.18 * h - leg * 0.5, 0.0]), mark("arms", [r * 1.2, 0.17 * h - arm * 0.5, 0.0])]
    neck, hs = p["neck"] * 0.08 * h, p["head"] * 0.09 * h
    n.append(seg([0.0, 0.2 * h, 0.0], [0.0, 0.2 * h + neck + hs * 0.2, 0.01 * h], r * 0.3, r * 0.27, 0, 1.3))
    n.extend(head(p, hs, [0.0, 0.2 * h + neck + hs, 0.01 * h], False))
    hip = -0.18 * h
    n.append(mir(limb([r * 0.45, hip, 0.0], [r * 0.45, hip - leg * 0.5, 0.03 * h], [r * 0.45, hip - leg, 0.0], t)))
    sh = 0.17 * h
    n.append(mir(limb([r * 0.95, sh, 0.0], [r * 1.15, sh - arm * 0.5, 0.02 * h], [r * 1.2, sh - arm, 0.05 * h], t * 0.8)))
    found = tail(p, [0.0, hip, -r * 0.7], h * 0.3, r * 0.2)
    if found:
        n.append(found)
        n.append(mark("tail", [0.0, hip + h * 0.1, -r * 0.7 - h * 0.15]))
    n.extend(wings(p, [r * 0.5, 0.15 * h, -r * 0.4], p["wings"] * h * 0.6))
    if p["wings"] > 0.05:
        n.append(mark("wings", [r * 0.5 + p["wings"] * h * 0.3, 0.2 * h, -r * 0.4]))
    return n


def bird(p) -> list[dict]:
    l = p["size"]
    r = 0.22 * l * p["build"]
    n = [lying(body_profile(l, r, 0.3), 2.2), mark("body", [0.0, r * 0.2, 0.0]),
         mark("legs", [r * 0.35, -r * 0.6 - 0.35 * l * p["legs"] * 0.5, 0.0])]
    reach = p["neck"] * l
    top = [0.0, r * 0.6 + reach * 0.3, l * 0.35 + reach * 0.15]
    n.append(seg([0.0, r * 0.3, l * 0.3], top, r * 0.5, r * 0.35, 0, 1.4))
    hs = p["head"] * 0.12 * l
    n.extend(head(p, hs, [top[0], top[1] + hs * 0.2, top[2] + hs * 0.4], True))
    n.extend(wings(p, [r * 0.5, r * 0.5, l * 0.15], p["wings"] * l * 0.9))
    if p["wings"] > 0.05:
        n.append(mark("wings", [r * 0.5 + p["wings"] * l * 0.45, r * 0.6, l * 0.1]))
    if p["tail"] > 0.05:
        n.append(mark("tail", [0.0, 0.0, -l * 0.45 - l * 0.2 * p["tail"]]))
        reach = l * 0.4 * p["tail"]
        for d in ([0.0, -0.1, -1.0], [0.35, -0.1, -1.0]):
            node = seg([0.0, 0.0, -l * 0.45], [d[0] * reach, d[1] * reach, -l * 0.45 + d[2] * reach], r * 0.35, r * 0.06, 2, 1.2)
            n.append(mir(node) if d[0] > 0.0 else node)
    h = 0.35 * l * p["legs"]
    n.append(mir(limb([r * 0.35, -r * 0.6, -l * 0.02], [r * 0.35, -r * 0.6 - h * 0.5, l * 0.02], [r * 0.35, -r * 0.6 - h, 0.0],
                      0.03 * l * p["leg_thick"])))
    return n


def fish(p) -> list[dict]:
    l = p["size"]
    r = 0.2 * l * p["build"]
    n = [lying(body_profile(l, r, 0.6), 2.2), mark("body", [r * 0.5, 0.0, 0.0]),
         mark("tail", [0.0, l * 0.12 * p["tail"], -l * 0.46 - l * 0.15 * p["tail"]])]
    n.append(mir(blob("sphere", [r * 0.62, r * 0.25, l * 0.33], [r * 0.14] * 3, 4, 3.0)))
    fin = l * 0.22 * p["tail"]
    for k in (1.0, -1.0):
        n.append(seg([0.0, 0.0, -l * 0.46], [0.0, k * fin, -l * 0.46 - fin * 0.8], r * 0.22, r * 0.03, 2, 1.2))
    if p["wings"] > 0.05:
        up = l * 0.2 * p["wings"]
        n.append(mark("fins", [0.0, r * 0.85 + up * 0.6, -l * 0.05]))
        n.append(seg([0.0, r * 0.85, l * 0.05], [0.0, r * 0.85 + up, -l * 0.12], r * 0.22, r * 0.02, 2, 1.2))
        n.append(mir(seg([r * 0.7, -r * 0.2, l * 0.15], [r * 0.7 + up * 0.8, -r * 0.2 - up * 0.5, -l * 0.02], r * 0.16, r * 0.02, 2, 1.1)))
    return n


def _insect_leg(z, r, legs, thick, l) -> dict:
    t = 0.012 * l * thick
    return group([seg([r * 0.6, 0.0, z], [r * 1.6, r * 0.9 * legs, z + l * 0.04], t * 1.3, t, 0, 1.2),
                  seg([r * 1.6, r * 0.9 * legs, z + l * 0.04], [r * 2.4 * legs, -r * 1.3 * legs, z + l * 0.07], t, t * 0.5, 0, 1.2)])


def insect(p) -> list[dict]:
    l = p["size"]
    r, hs = 0.14 * l * p["build"], p["head"] * 0.1 * l
    n = [blob("sphere", [0.0, 0.0, l * 0.42], [hs * 0.9, hs * 0.85, hs], 0, 1.8), blob("sphere", [0.0, 0.0, l * 0.18], [r * 0.9, r * 0.85, l * 0.14], 0, 2.0),
         blob("sphere", [0.0, 0.0, -l * 0.22], [r * 0.85, r * 0.8, l * 0.3], 1, 2.0),
         mir(blob("sphere", [hs * 0.5, hs * 0.25, l * 0.42 + hs * 0.6], [hs * 0.22] * 3, 4, 3.0)),
         mark("head", [0.0, hs, l * 0.42]), mark("thorax", [0.0, r, l * 0.18]), mark("abdomen", [0.0, r, -l * 0.22]),
         mark("legs", [r * 1.8, -r * 0.2, l * 0.1])]
    for k in range(max(1, min(6, p["pairs"]))):
        n.append(mir(_insect_leg(l * 0.2 - l * 0.12 * k, r, p["legs"], p["leg_thick"], l)))
    if p["horns"] > 0.05:
        n.append(mir(curve([hs * 0.3, hs * 0.5, l * 0.42 + hs * 0.6], [0.4, 1.0, 0.7], hs * p["horns"] * 2.0, 0.6, hs * 0.07, hs * 0.02, 2, 2)))
    if p["wings"] > 0.05:
        w = p["wings"] * l * 0.45
        n.append(mark("wings", [w * 0.9, r * 0.9, l * 0.1]))
        n.append(mir(blob("plane", [w * 0.62, r * 0.9, l * 0.12], [w * 0.6, 0.01, l * 0.2], 3, 1.2, [0.0, 0.0, -14.0])))
        n.append(mir(blob("plane", [w * 0.5, r * 0.8, -l * 0.1], [w * 0.45, 0.01, l * 0.14], 5, 1.2, [0.0, 0.0, -8.0])))
    return n


def serpent(p) -> list[dict]:
    l = p["size"]
    r, hs, end = 0.07 * l * p["build"], p["head"] * 0.06 * l, l * 0.5
    return [{"op": "sweep", "path": "wave", "from": [0.0, 0.0, -end], "dir": [0.0, 0.0, 1.0], "length": l,
             "bend": max(0.3, min(0.8, abs(p["tail_curl"]))), "r0": r * 0.1, "r1": r, "steps": 12, "color": 0, "weight": 2.0},
            blob("sphere", [0.0, 0.0, end + hs * 0.6], [hs * 0.9, hs * 0.7, hs * 1.3], 1, 2.0),
            mir(blob("sphere", [hs * 0.55, hs * 0.25, end + hs * 0.8], [hs * 0.15] * 3, 4, 3.0)),
            mark("head", [0.0, hs, end + hs * 0.6]), mark("body", [0.0, r * 1.2, 0.0]), mark("tail", [0.0, r * 0.5, -end])]


BUILDERS = {"biped": biped, "bird": bird, "fish": fish, "insect": insect, "serpent": serpent}


def compose(raw) -> dict:
    t = normalize(raw)
    return {"theme": t["theme"], "nodes": BUILDERS.get(t["plan"], quadruped)(t)}


def normalize_for_native(raw) -> dict:
    if not isinstance(raw, dict) or set(raw) - set(DEFAULTS):
        raise FormaError("bad_anatomy")
    out = dict(raw)
    for key in LIMITS:
        if key in out and not (isinstance(out[key], (int, float)) and not isinstance(out[key], bool) and math.isfinite(out[key])):
            del out[key]
    if "pairs" in out:
        pairs = out["pairs"]
        out["pairs"] = min(6, int(pairs)) if isinstance(pairs, (int, float)) and not isinstance(pairs, bool) and math.isfinite(pairs) and pairs >= 0 else 3
    return out


def sculpt(raw) -> dict:
    lib = _native()
    if lib is not None:
        try:
            return json.loads(lib.forma_anatomy_sculpt(json.dumps(normalize_for_native(raw), ensure_ascii=False)))
        except ValueError as exc:
            raise FormaError(str(exc)) from exc
    return compile_plan(compose(raw))


def _entries() -> list[dict]:
    return json.loads(PRESETS.read_text(encoding="utf-8"))


def _words(concept: str) -> list[str]:
    text = "".join(c.lower() if c.isalnum() else " " for c in str(concept)[:MAX_CONCEPT])
    return text.split()


def _matches(token: str, root: str) -> bool:
    if root.endswith("*"):
        return len(token) >= 3 and token.startswith(root[:-1])
    return token == root


def preset(concept: str) -> dict | None:
    lib = _native()
    if lib is not None:
        found = lib.forma_anatomy_preset(str(concept)[:MAX_CONCEPT])
        return json.loads(found) if found else None
    tokens = _words(concept)
    for entry in _entries():
        if any(_matches(t, r) for t in tokens for r in entry["roots"]):
            return {**DEFAULTS, **entry["anatomy"]}
    return None
