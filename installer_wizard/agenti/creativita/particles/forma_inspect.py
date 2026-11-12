import json
import math
import os

from agenti.particles import forma
from agenti.particles.forma import FormaError

TOUCH = 0.03
FLAT = 0.06
SPARSE = 5


def _native():
    if os.environ.get("NUXIVA_NATIVE", "auto").strip() == "0":
        return None
    try:
        import nuxiva_native
    except ImportError:
        return None
    return nuxiva_native if hasattr(nuxiva_native, "forma_inspect") else None


def _rotate(p, deg):
    rx, ry, rz = (math.radians(d) for d in deg)
    x, y, z = p
    y, z = y * math.cos(rx) - z * math.sin(rx), y * math.sin(rx) + z * math.cos(rx)
    x, z = x * math.cos(ry) + z * math.sin(ry), -x * math.sin(ry) + z * math.cos(ry)
    x, y = x * math.cos(rz) - y * math.sin(rz), x * math.sin(rz) + y * math.cos(rz)
    return x, y, z


def _bounds(part):
    lo, hi = [math.inf] * 3, [-math.inf] * 3
    sx, sy, sz = part["size"]
    for ix in (-1.0, 1.0):
        for iy in (-1.0, 1.0):
            for iz in (-1.0, 1.0):
                for axis, value in enumerate(_rotate((sx * ix, sy * iy, sz * iz), part["rot"])):
                    centre = part["at"][axis] + value
                    lo[axis], hi[axis] = min(lo[axis], centre), max(hi[axis], centre)
    return lo, hi


def _touches(a, b, gap) -> bool:
    return all(a[0][i] <= b[1][i] + gap and b[0][i] <= a[1][i] + gap for i in range(3))


def report(parts: list[dict], scale: float) -> dict:
    k = scale if math.isfinite(scale) and scale > 1e-9 else 1.0
    boxes = [_bounds(p) for p in parts]
    lo = [min(b[0][a] for b in boxes) for a in range(3)]
    hi = [max(b[1][a] for b in boxes) for a in range(3)]
    extent = [max(0.0, hi[a] - lo[a]) for a in range(3)]
    longest = max(extent)
    gap = TOUCH * longest
    parent = list(range(len(boxes)))

    def root(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    for i in range(len(boxes)):
        for j in range(i + 1, len(boxes)):
            if _touches(boxes[i], boxes[j], gap):
                ri, rj = root(i), root(j)
                parent[max(ri, rj)] = min(ri, rj)
    sizes = [0] * len(boxes)
    for i in range(len(boxes)):
        sizes[root(i)] += 1
    components = sum(1 for c in sizes if c > 0)
    main = max(range(len(sizes)), key=lambda i: (sizes[i], -i)) if sizes else 0
    loose = [{"shape": parts[i]["shape"], "at": [v / k for v in parts[i]["at"]]} for i in range(len(boxes)) if root(i) != main]
    mass = sum(p["weight"] for p in parts)
    moment = sum(p["weight"] * p["at"][0] for p in parts)
    asymmetry = abs(moment / mass) / extent[0] if mass > 0 and extent[0] > 0 else 0.0
    issues = []
    if components > 1:
        issues.append("detached_parts")
    if longest > 0 and min(extent) < FLAT * longest:
        issues.append("flat")
    if len(parts) < SPARSE:
        issues.append("too_few_parts")
    return {"parts": len(parts), "extent": [v / k for v in extent], "components": components, "loose": loose, "asymmetry": asymmetry,
            "issues": issues}


def inspect(plan) -> dict:
    lib = _native()
    if lib is not None:
        try:
            return json.loads(lib.forma_inspect(json.dumps(plan, ensure_ascii=False)))
        except ValueError as exc:
            raise FormaError(str(exc)) from exc
    spec, k = forma.compile_scaled(plan)
    return report(spec["parts"], k)
