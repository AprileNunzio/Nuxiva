import json
import math
import time

import native_core

from agenti.nodes import telemetry_engine as py


def _plain(raw):
    if not isinstance(raw, dict):
        return {}
    return {str(k): v for k, v in raw.items() if isinstance(v, (bool, int, float)) and math.isfinite(float(v))}


def _call(name: str, python, args: tuple, fallback_args: tuple):
    native = native_core.symbol(name)
    if native is not None:
        return json.loads(native(*args))
    native_core.python_fallback("node_telemetry")
    return python(*fallback_args)


def clean_metrics(raw) -> dict:
    plain = _plain(raw)
    return _call("node_clean_metrics", py.clean_metrics, (json.dumps(plain),), (plain,)) if plain else {}


def clean_proximity(raw, now: float | None = None) -> dict:
    moment = now if now is not None else time.time()
    cleaned = _plain(raw)
    if not cleaned:
        return {}
    return _call("node_clean_proximity", py.clean_proximity, (json.dumps(cleaned), float(moment)), (cleaned, float(moment)))


def nearest(nodes: list[dict], now: float | None = None) -> dict:
    moment = now if now is not None else time.time()
    view = [{"id": str(n["id"]), "online": bool(n.get("online")), "proximity": n.get("proximity") or {}} for n in nodes]
    return _call("node_nearest", py.nearest, (json.dumps(view), float(moment)), (view, float(moment)))
