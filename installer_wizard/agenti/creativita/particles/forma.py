import json
import math
import os

MAX_PARTS = 96
MAX_PRIMS = 256
MAX_NODES = 128
MAX_DEPTH = 5
MAX_PROFILE = 16
MAX_STEPS = 12
MAX_COUNT = 24
REACH = 3.0
LIMIT = 100.0
SHAPES = ("sphere", "box", "cylinder", "cone", "torus", "helix", "plane", "cloud", "disc", "spiral", "ring", "halo", "orbit")
AXES = ("x", "y", "z")
PATHS = ("line", "arc", "wave", "spiral")
PALETTES = {
    "bioluminescent": ("#4ce6ff", "#7952ec", "#a87bff", "#ff6be5", "#5ef2ff", "#c49bff"),
    "celestial": ("#ffd166", "#5ce1e6", "#480ca8", "#72efdd", "#9b7bff", "#ff9f1c"),
    "botanical": ("#38b000", "#70e000", "#a7c957", "#ff70a6", "#ffb703", "#007200"),
    "fauna": ("#ee9b00", "#ca6702", "#bb3e03", "#0077b6", "#90e0ef", "#f1faee"),
    "mechanical": ("#64dfdf", "#48bfe3", "#5390d9", "#ff9f1c", "#80ffdb", "#7400b8"),
    "microscopic": ("#ff006e", "#00f5d4", "#8338ec", "#fee440", "#3a86ff", "#ffbe0b"),
    "geological": ("#2ec4b6", "#e71d36", "#ff9f1c", "#7209b7", "#e0aaff", "#c77dff"),
    "ethereal": ("#5ef2ff", "#9b7bff", "#66ffe3", "#ff7be5", "#7aa2ff", "#ffd166"),
}
FIELDS = {
    "lathe": {"op", "profile", "color", "weight"},
    "sweep": {"op", "path", "from", "dir", "length", "bend", "r0", "r1", "steps", "color", "weight"},
    "blob": {"op", "shape", "at", "size", "rot", "color", "weight"},
    "radial": {"op", "count", "radius", "phase", "child"},
    "mirror": {"op", "axis", "child"},
    "rotate": {"op", "axis", "deg", "child"},
    "group": {"op", "children"},
    "mark": {"op", "name", "at"},
}


class FormaError(ValueError):
    pass


def _num(value) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or abs(value) > LIMIT:
        raise FormaError("out_of_range")
    return float(value)


def _vec(value, default) -> list[float]:
    if value is None:
        return list(default)
    if not isinstance(value, (list, tuple)) or len(value) != 3:
        raise FormaError("out_of_range")
    return [_num(v) for v in value]


def _count(value, default: int) -> int:
    if value is None:
        return default
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise FormaError("bad_count")
    return value


def _sub(a, b):
    return [a[0] - b[0], a[1] - b[1], a[2] - b[2]]


def _add(a, b):
    return [a[0] + b[0], a[1] + b[1], a[2] + b[2]]


def _scale(a, k):
    return [a[0] * k, a[1] * k, a[2] * k]


def _cross(a, b):
    return [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]]


def _norm(a) -> float:
    return math.sqrt(a[0] * a[0] + a[1] * a[1] + a[2] * a[2])


def _unit(a):
    n = _norm(a)
    return _scale(a, 1.0 / n) if n > 1e-9 else None


def _rotate(p, axis: str, deg: float):
    sin, cos = math.sin(math.radians(deg)), math.cos(math.radians(deg))
    x, y, z = p
    if axis == "x":
        return [x, y * cos - z * sin, y * sin + z * cos]
    if axis == "y":
        return [x * cos + z * sin, y, -x * sin + z * cos]
    return [x * cos - y * sin, x * sin + y * cos, z]


def _mirror(p, axis: str):
    q = list(p)
    q["xyz".index(axis)] *= -1.0
    return q


def _move(prim: dict, fn, yaw: float) -> dict:
    out = dict(prim)
    if prim["kind"] == "mark":
        out["at"] = fn(prim["at"])
    elif prim["kind"] == "seg":
        out["a"], out["b"] = fn(prim["a"]), fn(prim["b"])
    else:
        out["at"] = fn(prim["at"])
        out["rot"] = [prim["rot"][0], prim["rot"][1] + yaw, prim["rot"][2]]
    return out


class _Builder:
    def __init__(self) -> None:
        self.nodes = 0
        self.out: list[dict] = []

    def room(self, extra: int) -> None:
        if len(self.out) + extra > MAX_PRIMS:
            raise FormaError("too_many_parts")

    def child(self, node, depth: int) -> list[dict]:
        outer, self.out = self.out, []
        try:
            self.emit(node, depth)
            return self.out
        finally:
            self.out = outer

    def emit(self, node, depth: int) -> None:
        self.nodes += 1
        if self.nodes > MAX_NODES or depth > MAX_DEPTH:
            raise FormaError("too_complex")
        if not isinstance(node, dict) or node.get("op") not in FIELDS or set(node) - FIELDS[node["op"]]:
            raise FormaError("bad_node")
        getattr(self, "_" + node["op"])(node, depth)

    def _group(self, node, depth: int) -> None:
        children = node.get("children")
        if not isinstance(children, list):
            raise FormaError("bad_node")
        for item in children:
            self.emit(item, depth + 1)

    def _lathe(self, node, depth: int) -> None:
        profile = node.get("profile")
        if not isinstance(profile, list) or not 2 <= len(profile) <= MAX_PROFILE:
            raise FormaError("bad_profile")
        weight, color = _num(node.get("weight", 1.0)), _count(node.get("color"), 0)
        self.room(len(profile))
        rows = []
        for row in profile:
            if not isinstance(row, (list, tuple)) or len(row) != 2:
                raise FormaError("bad_profile")
            rows.append((_num(row[0]), _num(row[1])))
        for (r0, y0), (r1, y1) in zip(rows, rows[1:]):
            if r0 < 0 or r1 < 0:
                raise FormaError("bad_profile")
            self.out.append({"kind": "seg", "a": [0.0, y0, 0.0], "b": [0.0, y1, 0.0], "r0": r0, "r1": r1, "color": color, "weight": weight})

    def _sweep(self, node, depth: int) -> None:
        path = node.get("path", "line")
        if path not in PATHS:
            raise FormaError("bad_sweep")
        origin, heading = _vec(node.get("from"), (0.0, 0.0, 0.0)), _vec(node.get("dir"), (0.0, 1.0, 0.0))
        length, bend = _num(node.get("length", 1.0)), _num(node.get("bend", 0.0))
        r0, r1, weight = _num(node.get("r0", 0.1)), _num(node.get("r1", 0.1)), _num(node.get("weight", 1.0))
        steps, color = _count(node.get("steps"), 4), _count(node.get("color"), 0)
        if not 1 <= steps <= MAX_STEPS or r0 < 0 or r1 < 0:
            raise FormaError("bad_sweep")
        d = _unit(heading)
        u = _unit(_cross(d, [0.0, 1.0, 0.0] if abs(d[1]) < 0.9 else [1.0, 0.0, 0.0])) if d else None
        if d is None or u is None:
            raise FormaError("bad_sweep")
        v = _cross(d, u)
        self.room(steps)
        bend = max(-2.0, min(2.0, bend))

        def at(t: float):
            if path == "line":
                off = [0.0, 0.0, 0.0]
            elif path == "arc":
                off = _scale(u, bend * length * t * t * 0.5)
            elif path == "wave":
                off = _scale(u, bend * length * 0.25 * math.sin(math.tau * t))
            else:
                theta = math.tau * 1.5 * t
                off = _scale(_add(_scale(u, math.cos(theta) - 1.0), _scale(v, math.sin(theta))), abs(bend) * length * 0.3 * t)
            return _add(_add(origin, _scale(d, length * t)), off)

        for i in range(steps):
            t0, t1 = i / steps, (i + 1) / steps
            self.out.append({"kind": "seg", "a": at(t0), "b": at(t1), "r0": r0 + (r1 - r0) * t0, "r1": r0 + (r1 - r0) * t1,
                             "color": color, "weight": weight})

    def _blob(self, node, depth: int) -> None:
        shape = node.get("shape", "sphere")
        if shape not in SHAPES:
            raise FormaError("bad_node")
        item = {"kind": "blob", "shape": shape, "at": _vec(node.get("at"), (0.0, 0.0, 0.0)), "size": _vec(node.get("size"), (1.0, 1.0, 1.0)),
                "rot": _vec(node.get("rot"), (0.0, 0.0, 0.0)), "color": _count(node.get("color"), 0), "weight": _num(node.get("weight", 1.0))}
        self.room(1)
        self.out.append(item)

    def _mark(self, node, depth: int) -> None:
        name = node.get("name")
        if not isinstance(name, str) or not 1 <= len(name.encode()) <= 32:
            raise FormaError("bad_mark")
        item = {"kind": "mark", "name": name, "at": _vec(node.get("at"), (0.0, 0.0, 0.0))}
        self.room(1)
        self.out.append(item)

    def _radial(self, node, depth: int) -> None:
        radius, phase = _num(node.get("radius", 0.0)), _num(node.get("phase", 0.0))
        count = node.get("count")
        if isinstance(count, bool) or not isinstance(count, int) or not 1 <= count <= MAX_COUNT:
            raise FormaError("bad_count")
        inner = self.child(node.get("child"), depth + 1)
        self.room(len(inner) * count)
        for i in range(count):
            angle = phase + 360.0 * i / count
            self.out.extend(_move(p, lambda q, a=angle: _rotate(_add(q, [radius, 0.0, 0.0]), "y", a), angle) for p in inner)

    @staticmethod
    def _axis(node) -> str:
        if node.get("axis") not in AXES:
            raise FormaError("bad_node")
        return node["axis"]

    def _mirror(self, node, depth: int) -> None:
        axis = self._axis(node)
        inner = self.child(node.get("child"), depth + 1)
        self.room(len(inner) * 2)
        flipped = [_move(p, lambda q: _mirror(q, axis), 0.0) for p in inner]
        self.out.extend(inner)
        self.out.extend(flipped)

    def _rotate(self, node, depth: int) -> None:
        axis, deg = self._axis(node), _num(node.get("deg"))
        inner = self.child(node.get("child"), depth + 1)
        self.room(len(inner))
        self.out.extend(_move(p, lambda q: _rotate(q, axis, deg), deg if axis == "y" else 0.0) for p in inner)


def _reach(prims: list[dict]) -> float:
    best = 0.0
    for p in prims:
        if p["kind"] == "mark":
            continue
        if p["kind"] == "seg":
            ext = max(max(abs(v) for v in p["a"]), max(abs(v) for v in p["b"])) + max(p["r0"], p["r1"])
        else:
            ext = max(abs(v) for v in p["at"]) + max(p["size"])
        best = max(best, ext)
    return best


def _wrap(deg: float) -> float:
    m = deg % 360.0
    return m - 360.0 if m > 180.0 else m


def _seg(p: dict, k: float):
    a, b, r0, r1 = p["a"], p["b"], p["r0"], p["r1"]
    wide, narrow, hi, lo = (a, b, r0, r1) if r0 >= r1 else (b, a, r1, r0)
    axis = _sub(narrow, wide)
    length = _norm(axis)
    if length < 1e-9:
        return None
    dx, dy, dz = _scale(axis, 1.0 / length)
    rx = math.degrees(math.acos(max(-1.0, min(1.0, dy))))
    ry = math.degrees(math.atan2(dx, dz))
    mid = _scale(_add(wide, narrow), 0.5)
    shape, radius = ("cone", hi) if hi > 0.0 and lo < 0.25 * hi else ("cylinder", (hi + lo) * 0.5)
    half = max(0.01, min(10.0, length * 0.5 * k))
    r = max(0.01, min(10.0, radius * k))
    return shape, [r, half, r], _scale(mid, k), [rx, ry, 0.0]


def compile_plan(plan) -> dict:
    if not isinstance(plan, dict) or set(plan) - {"theme", "nodes"} or not isinstance(plan.get("nodes"), list):
        raise FormaError("bad_plan")
    builder = _Builder()
    for node in plan["nodes"]:
        builder.emit(node, 0)
    extent = _reach(builder.out)
    if not builder.out or extent <= 1e-9:
        raise FormaError("empty")
    k = REACH / extent
    colors = PALETTES.get(plan.get("theme", "ethereal"), PALETTES["ethereal"])
    parts = []
    labels: list[dict] = []
    for p in builder.out:
        if p["kind"] == "mark":
            if all(item["name"] != p["name"] for item in labels):
                labels.append({"name": p["name"], "at": _scale(p["at"], k)})
            continue
        weight = max(0.05, min(10.0, p["weight"]))
        if p["kind"] == "seg":
            built = _seg(p, k)
            if built is not None:
                shape, size, at, rot = built
                parts.append({"shape": shape, "size": size, "at": at, "rot": rot, "color": colors[p["color"] % 6], "weight": weight})
        else:
            parts.append({"shape": p["shape"], "size": [max(0.01, min(10.0, v * k)) for v in p["size"]], "at": _scale(p["at"], k),
                          "rot": [_wrap(v) for v in p["rot"]], "color": colors[p["color"] % 6], "weight": weight})
    if not parts or len(parts) > MAX_PARTS:
        raise FormaError("too_many_parts")
    return {"parts": parts, "labels": labels} if labels else {"parts": parts}


def _native():
    if os.environ.get("NUXIVA_NATIVE", "auto").strip() == "0":
        return None
    try:
        import nuxiva_native
    except ImportError:
        return None
    return nuxiva_native if hasattr(nuxiva_native, "forma_compile") else None


def build(plan) -> dict:
    lib = _native()
    if lib is None:
        return compile_plan(plan)
    try:
        return json.loads(lib.forma_compile(json.dumps(plan, ensure_ascii=False)))
    except ValueError as exc:
        raise FormaError(str(exc)) from exc
