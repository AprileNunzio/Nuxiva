from __future__ import annotations

import json
import math
import re
from typing import Any

try:
    from nuxiva_native import resource_plan as _native_plan
except ImportError:
    _native_plan = None

MAX_INPUT = 1024 * 1024
MAX_COMPONENTS = 512
ID_RE = re.compile(r"^[a-z0-9_.:-]{1,64}$")
LEVELS = ("calm", "elevated", "high", "critical")
CLASSES = ("protected", "high", "normal", "low")
KINDS = ("process", "model", "widget", "cache", "surface")
ENTER = (60.0, 75.0, 90.0)
MARGIN = 8.0
IDLE_MS = {"calm": 1_800_000, "elevated": 600_000, "high": 180_000, "critical": 30_000}
SHARE = {"calm": 100, "elevated": 80, "high": 60, "critical": 40}
CLASS_SHARE = {"protected": 30, "high": 20, "normal": 10, "low": 5}
U64 = (1 << 64) - 1
SYSTEM_UINTS = ("cores", "mem_total", "mem_available", "swap_total", "swap_used", "gpu_mem_total", "gpu_mem_used")


def _scale(system: dict) -> tuple[int, int]:
    ram, cores = system["mem_total"], system["cores"]
    if ram >= 24 << 30 and cores >= 8:
        return 4, 1
    if ram >= 12 << 30 and cores >= 4:
        return 2, 1
    if ram >= 6 << 30:
        return 1, 1
    return 1, 2


def native_available() -> bool:
    return _native_plan is not None


def _uint(value: Any) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0 or value > U64:
        raise ValueError("resource.invalid")
    return value


def _num(value: Any) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError("resource.invalid")
    return float(value)


def _round1(value: float) -> float:
    return math.floor(value * 10.0 + 0.5) / 10.0


def _ratio(used: int, total: int) -> float:
    return 0.0 if total == 0 else min(100.0, max(0.0, used / total * 100.0))


def _clean(value: float) -> float:
    return min(100.0, max(0.0, value))


def _parse(raw: dict) -> dict:
    sys_raw = raw.get("system")
    if not isinstance(sys_raw, dict):
        raise ValueError("resource.invalid")
    system = {k: _uint(sys_raw.get(k, 0)) for k in SYSTEM_UINTS}
    system["cpu_percent"] = _num(sys_raw.get("cpu_percent", 0.0))
    system["gpu_percent"] = _num(sys_raw.get("gpu_percent", 0.0))
    if system["mem_total"] <= 0 or "mem_total" not in sys_raw or "mem_available" not in sys_raw:
        raise ValueError("resource.invalid")
    items = raw.get("components", [])
    if not isinstance(items, list) or len(items) > MAX_COMPONENTS:
        raise ValueError("resource.invalid")
    components = []
    for c in items:
        if not isinstance(c, dict):
            raise ValueError("resource.invalid")
        cid = c.get("id")
        if not isinstance(cid, str) or not ID_RE.fullmatch(cid) or c.get("kind") not in KINDS or c.get("class") not in CLASSES:
            raise ValueError("resource.invalid")
        budget = c.get("budget")
        flags = (c.get("visible", True), c.get("reclaimable", False))
        if not all(isinstance(f, bool) for f in flags):
            raise ValueError("resource.invalid")
        components.append({
            "id": cid, "kind": c["kind"], "class": c["class"], "rss": _uint(c.get("rss", 0)),
            "budget": None if budget is None else _uint(budget), "idle_ms": _uint(c.get("idle_ms", 0)),
            "visible": flags[0], "reclaimable": flags[1], "cpu_percent": _num(c.get("cpu_percent", 0.0)),
        })
    previous = raw.get("previous")
    if previous is not None and previous not in LEVELS:
        raise ValueError("resource.invalid")
    return {"system": system, "components": components, "previous": previous}


def _mem_percent(system: dict) -> float:
    available = min(system["mem_available"], system["mem_total"])
    return _round1(_ratio(system["mem_total"] - available, system["mem_total"]))


def _pressure(system: dict) -> float:
    mem = max(0.0, _mem_percent(system) - 50.0) * 2.0
    swap = _ratio(system["swap_used"], system["swap_total"]) * 1.5
    gpu_mem = _ratio(system["gpu_mem_used"], system["gpu_mem_total"])
    value = max(_clean(system["cpu_percent"]), _clean(system["gpu_percent"]), gpu_mem, mem, swap)
    return _round1(min(100.0, max(0.0, value)))


def _classify(score: float, previous: str | None) -> str:
    rank = 0
    for index, enter in enumerate(ENTER):
        if score >= enter:
            rank = index + 1
    if previous is not None:
        prev = LEVELS.index(previous)
        if rank < prev and score >= ENTER[prev - 1] - MARGIN:
            rank = prev
    return LEVELS[rank]


def _budget(c: dict, total: int, level: str) -> int:
    if c["budget"] is not None:
        return c["budget"] if c["class"] == "protected" else c["budget"] * SHARE[level] // 100
    base = total * CLASS_SHARE[c["class"]] // 100
    return base if c["class"] == "protected" else base * SHARE[level] // 100


def _release(kind: str) -> str:
    return {"model": "unload", "widget": "hibernate", "surface": "hibernate", "cache": "drop"}.get(kind, "trim")


def _decide(c: dict, level: str, budget: int, cpu_busy: bool, scale: tuple[int, int]) -> tuple[str, str, int] | None:
    rank = LEVELS.index(level)
    if c["kind"] == "surface" and not c["visible"]:
        return "suspend", "hidden_surface", c["rss"]
    if not c["reclaimable"]:
        return None
    if c["idle_ms"] >= IDLE_MS[level] * scale[0] // scale[1] and not c["visible"]:
        return _release(c["kind"]), "idle", c["rss"]
    if rank >= 3 and c["class"] == "low":
        return _release(c["kind"]), "critical_pressure", c["rss"]
    if c["rss"] > budget and rank >= 1:
        return ("drop" if c["kind"] == "cache" else "trim"), "over_budget", c["rss"] - budget
    if cpu_busy and rank >= 2 and c["cpu_percent"] >= 50.0 and not c["visible"]:
        return "throttle", "cpu_hog", 0
    return None


def _plan(data: dict) -> dict:
    system = data["system"]
    score = _pressure(system)
    level = _classify(score, data["previous"])
    cpu_busy = system["cpu_percent"] >= 75.0
    scale = _scale(system)
    actions, budgets, protected = [], [], set()
    for c in data["components"]:
        budget = _budget(c, system["mem_total"], level)
        budgets.append({"id": c["id"], "budget": budget, "rss": c["rss"], "over": c["rss"] > budget})
        if c["class"] == "protected":
            protected.add(c["id"])
            continue
        decision = _decide(c, level, budget, cpu_busy, scale)
        if decision:
            actions.append({"id": c["id"], "action": decision[0], "reason": decision[1], "reclaim": decision[2]})
    actions.sort(key=lambda a: (0 if a["action"] == "suspend" else 1, -a["reclaim"], a["id"]))
    budgets.sort(key=lambda b: b["id"])
    return {"level": level, "pressure": score, "mem_percent": _mem_percent(system), "actions": actions,
            "budgets": budgets, "reclaim_total": min(U64, sum(a["reclaim"] for a in actions)), "protected": sorted(protected)}


def plan_python(raw: str) -> dict:
    if len(raw) > MAX_INPUT:
        raise ValueError("resource.too_large")
    try:
        data = json.loads(raw)
    except ValueError:
        raise ValueError("resource.invalid") from None
    if not isinstance(data, dict):
        raise ValueError("resource.invalid")
    return _plan(_parse(data))


def plan(payload: dict) -> dict:
    raw = json.dumps(payload, separators=(",", ":"), allow_nan=False)
    if _native_plan is not None:
        return json.loads(_native_plan(raw))
    return plan_python(raw)
