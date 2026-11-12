import math
import random

from features.diorama import spec as S
from features.diorama.catalog import BY_ID
from features.diorama.reference import DIMS, ENTRIES

GROUND = frozenset({"grass_patch", "path", "pond", "petals", "road", "rails", "platform", "moat", "hill", "drawbridge"})
MOVERS = frozenset({"train", "car", "person"})
FORTIFICATION = frozenset(k.id for k in BY_ID.values() if k.group == "Fortificazioni")
MARGIN = 0.25
FIT = 0.82
GRID = (5, 4)


def _defaults(kind: str) -> dict:
    return {name: p.default for name, p in BY_ID[kind].params.items()}


def footprint(item: dict) -> tuple[float, float]:
    kind = item["kind"]
    if kind not in DIMS:
        return 0.8 * item["scale"], 0.8 * item["scale"]
    values = {**_defaults(kind), **{k: v for k, v in item["params"].items() if isinstance(v, (int, float)) and not isinstance(v, bool)}}
    w, d, _ = DIMS[kind](values)
    angle = math.radians(item["rot"])
    c, s = abs(math.cos(angle)), abs(math.sin(angle))
    return (c * w + s * d) / 2 * item["scale"], (s * w + c * d) / 2 * item["scale"]


def hill_height(items: list[dict], x: float, z: float) -> float:
    best = 0.0
    for item in items:
        if item["kind"] != "hill":
            continue
        radius = float(item["params"].get("radius", 5)) * item["scale"]
        height = float(item["params"].get("height", 1.6)) * item["scale"]
        distance = math.hypot(x - item["x"], z - item["z"])
        if distance < radius:
            best = max(best, item["y"] + height * math.sin((1 - distance / radius) * math.pi / 2) ** 0.9)
    return best


def _solid(item: dict) -> bool:
    return item["kind"] not in GROUND and item["kind"] not in MOVERS and not item["kind"].startswith("x_")


def _collides(a: dict, b: dict) -> bool:
    if a["kind"] in FORTIFICATION and b["kind"] in FORTIFICATION:
        return False
    ax, az = footprint(a)
    bx, bz = footprint(b)
    return abs(a["x"] - b["x"]) < (ax + bx) * FIT and abs(a["z"] - b["z"]) < (az + bz) * FIT


def _push(moving: dict, fixed: dict) -> None:
    ax, az = footprint(moving)
    bx, bz = footprint(fixed)
    dx, dz = moving["x"] - fixed["x"], moving["z"] - fixed["z"]
    over_x = (ax + bx) * FIT - abs(dx)
    over_z = (az + bz) * FIT - abs(dz)
    if over_x < over_z:
        moving["x"] += (1 if dx >= 0 else -1) * (over_x + 0.05)
    else:
        moving["z"] += (1 if dz >= 0 else -1) * (over_z + 0.05)


def _clamp(item: dict, base: dict) -> None:
    hx, hz = footprint(item)
    limit_x, limit_z = base["w"] / 2 - MARGIN, base["d"] / 2 - MARGIN
    item["x"] = max(-limit_x + min(hx, limit_x), min(limit_x - min(hx, limit_x), item["x"])) if item["kind"] not in GROUND else max(-limit_x, min(limit_x, item["x"]))
    item["z"] = max(-limit_z + min(hz, limit_z), min(limit_z - min(hz, limit_z), item["z"])) if item["kind"] not in GROUND else max(-limit_z, min(limit_z, item["z"]))


def settle(rows: list[dict], existing: list[dict], base: dict) -> list[dict]:
    placed = [dict(i) for i in existing]
    out = []
    for row in rows:
        item = {**row, "params": dict(row["params"])}
        _clamp(item, base)
        if _solid(item):
            others = [o for o in placed if _solid(o)]
            for _ in range(4):
                hit = next((o for o in others if _collides(item, o)), None)
                if not hit:
                    break
                _push(item, hit)
                _clamp(item, base)
        if item["kind"] not in ("hill", "moat", "path", "road", "rails", "platform", "grass_patch", "pond", "petals"):
            item["y"] = round(max(item["y"], hill_height(placed, item["x"], item["z"])), 3)
        placed.append(item)
        out.append(item)
    return out


def empty_cells(items: list[dict], base: dict) -> list[dict]:
    cols, rows = GRID
    cw, cd = base["w"] / cols, base["d"] / rows
    counts = [[0] * cols for _ in range(rows)]
    for item in items:
        if item["kind"] in GROUND:
            continue
        c = min(cols - 1, max(0, int((item["x"] + base["w"] / 2) / cw)))
        r = min(rows - 1, max(0, int((item["z"] + base["d"] / 2) / cd)))
        counts[r][c] += 1
    cells = []
    for r in range(rows):
        for c in range(cols):
            if counts[r][c] < 2:
                cells.append({"x0": round(-base["w"] / 2 + c * cw, 1), "x1": round(-base["w"] / 2 + (c + 1) * cw, 1),
                              "z0": round(-base["d"] / 2 + r * cd, 1), "z1": round(-base["d"] / 2 + (r + 1) * cd, 1), "count": counts[r][c]})
    return cells


def dress(items: list[dict], base: dict, palette: dict, rng: random.Random) -> list[dict]:
    extra = []
    green = palette.get("grass") if isinstance(palette.get("grass"), str) else "#4f7d3a"
    for cell in empty_cells(items, base):
        for _ in range(2 - cell["count"]):
            x, z = rng.uniform(cell["x0"] + 0.4, cell["x1"] - 0.4), rng.uniform(cell["z0"] + 0.4, cell["z1"] - 0.4)
            kind = rng.choice(("bush", "bush", "rock"))
            params = {"radius": round(rng.uniform(0.3, 0.7), 2), "color": green} if kind == "bush" else {"radius": round(rng.uniform(0.2, 0.55), 2)}
            extra.append({"kind": kind, "x": x, "z": z, "y": 0, "rot": rng.uniform(0, 360), "scale": 1, "params": params, "motion": {}})
    return S.clean_items(extra)


__all__ = ["ENTRIES", "settle", "dress", "empty_cells", "footprint", "hill_height"]
