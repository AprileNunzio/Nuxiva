import json
import math

from features.stage import native

SHOWN_AT = 50.0
MIN_AT = 20.0
MARGIN = 6.0
WEIGHT_LIMIT = 40.0
MAX_SURFACES = 128
STATES = ("shown", "min", "hidden")
AMBIENT = frozenset({"rail_voice", "rail_home", "rail_scan", "rail_vitals", "rail_learned", "project", "music_clock",
                     "brain_badge", "thinking"})


def context_key(ctx: dict) -> str:
    mode = ctx.get("mode") or ""
    if mode and mode != "face":
        return mode
    if ctx.get("typing"):
        return "typing"
    if ctx.get("conversing") or ctx.get("listening") or ctx.get("speaking"):
        return "voice"
    if not ctx.get("people"):
        return "empty"
    return "idle"


def _adjust(sid: str, ctx: dict, key: str) -> tuple[float, str | None]:
    voice = key == "voice"
    mode = ctx.get("mode") or ""
    desk = ctx.get("desk") or []
    if mode and mode != "face" and sid in AMBIENT:
        return 0.0, "hidden"
    people = ctx.get("people") or 0
    if sid == "chat":
        if ctx.get("typing"):
            return 0.0, "shown"
        if voice:
            return -30.0, None
        if key == "empty":
            return -10.0, None
    elif sid == "thinking":
        if ctx.get("typing"):
            return -40.0, None
    elif sid in ("rail_scan", "rail_vitals", "rail_learned") and people == 0:
        return 0.0, "hidden"
    elif sid == "rail_scan":
        if voice:
            return -5.0, None
    elif sid in ("rail_vitals", "rail_learned"):
        if voice:
            return -35.0, None
    elif sid == "project":
        if not ctx.get("project") or "project_status" in desk:
            return 0.0, "hidden"
        if voice:
            return -10.0, None
    elif sid == "rail_home":
        if voice:
            return -10.0, None
    elif sid == "music_clock":
        if not ctx.get("music") or "music" in desk:
            return 0.0, "hidden"
    elif sid == "brain_badge":
        if voice:
            return -20.0, None
    return 0.0, None


def _band(score: float) -> str:
    return "shown" if score >= SHOWN_AT else "min" if score >= MIN_AT else "hidden"


RANK = {"shown": 2, "min": 1, "hidden": 0}


def _settle(score: float, target: str, prev: dict | None, dwell: int, now: int) -> str:
    if not prev or prev["state"] == target:
        return target
    if max(0, now - prev["since_ms"]) < dwell:
        return prev["state"]
    if RANK[target] > RANK[prev["state"]]:
        edge = MIN_AT if RANK[prev["state"]] == 0 else SHOWN_AT
        ok = score >= edge + MARGIN
    else:
        edge = SHOWN_AT if RANK[prev["state"]] == 2 else MIN_AT
        ok = score < edge - MARGIN
    return target if ok else prev["state"]


def _finite(value, default: float = 0.0) -> float:
    try:
        v = float(value)
    except (TypeError, ValueError):
        return default
    return v if math.isfinite(v) else default


def plan_python(req: dict) -> dict:
    now = int(req.get("now_ms") or 0)
    ctx = req.get("context") or {}
    key = context_key(ctx)
    previous = req.get("previous") or {}
    weights = req.get("weights") or {}
    specs = list(req.get("surfaces") or [])[:MAX_SURFACES]
    out: dict[str, dict] = {}
    for spec in specs:
        sid = spec["id"]
        prev = previous.get(sid)
        raw = (weights.get(sid) or {}).get(key)
        weight = max(-WEIGHT_LIMIT, min(WEIGHT_LIMIT, _finite(raw))) if raw is not None else 0.0
        base = _finite(spec.get("priority"))
        if spec.get("pinned"):
            delta, hard = 0.0, "shown"
        elif spec.get("enabled", True) is False:
            delta, hard = 0.0, "hidden"
        else:
            delta, hard = _adjust(sid, ctx, key)
        score = max(0.0, min(100.0, base + delta + weight))
        state = hard or _settle(score, _band(score), prev, int(spec.get("dwell_ms") or 0), now)
        since = prev["since_ms"] if prev and prev["state"] == state else now
        out[sid] = {"state": state, "score": score, "since_ms": since}
    groups: dict[str, list[str]] = {}
    for spec in specs:
        if spec.get("group"):
            groups.setdefault(spec["group"], []).append(spec["id"])
    for members in groups.values():
        alive = [m for m in members if m in out and out[m]["state"] != "hidden"]
        winner = None
        for m in alive:
            if winner is None or out[m]["score"] > out[winner]["score"] or (
                    out[m]["score"] == out[winner]["score"] and m < winner):
                winner = m
        for m in members:
            if m != winner and m in out and out[m]["state"] != "hidden":
                out[m] = {**out[m], "state": "hidden", "since_ms": now}
    return {"context_key": key, "surfaces": dict(sorted(out.items()))}


def plan(req: dict) -> dict:
    if native.lib is not None:
        return json.loads(native.lib.stage_plan(json.dumps(req, separators=(",", ":"))))
    return plan_python(req)
