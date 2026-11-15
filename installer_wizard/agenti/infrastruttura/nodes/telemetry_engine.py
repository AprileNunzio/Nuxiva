import math
import time

METRIC_LIMITS = {
    "cpu": (0.0, 100.0),
    "ram": (0.0, 100.0),
    "disk": (0.0, 100.0),
    "gpu": (0.0, 100.0),
    "battery": (0.0, 100.0),
    "temp": (-60.0, 200.0),
    "uptime": (0.0, 1e10),
    "power_w": (0.0, 5000.0),
    "rtt_ms": (0.0, 60000.0),
    "rx_kbps": (0.0, 1e9),
    "tx_kbps": (0.0, 1e9),
    "charging": (0.0, 1.0),
}
PROXIMITY_LIMITS = {
    "audio_level": (0.0, 1.0),
    "speech": (0.0, 1.0),
    "face": (0.0, 1.0),
    "motion": (0.0, 1.0),
    "screen_on": (0.0, 1.0),
}
PROXIMITY_WEIGHTS = {"speech": 0.4, "audio_level": 0.25, "face": 0.25, "motion": 0.1}
PROXIMITY_TTL = 45.0
PROXIMITY_FLOOR = 0.12
HALF_LIFE = 12.0
MARGIN = 0.08
CLOCK_SKEW = 5.0


def _bounded(raw, limits: dict) -> dict:
    if not isinstance(raw, dict):
        return {}
    out = {}
    for key, (low, high) in limits.items():
        value = raw.get(key)
        if isinstance(value, bool):
            value = float(value)
        if isinstance(value, (int, float)) and math.isfinite(value):
            out[key] = round(max(low, min(high, float(value))), 3 if high <= 1.0 else 1)
    return out


def clean_metrics(raw) -> dict:
    return _bounded(raw, METRIC_LIMITS)


def clean_proximity(raw, now: float | None = None) -> dict:
    out = _bounded(raw, PROXIMITY_LIMITS)
    if out:
        out["at"] = round(now if now is not None else time.time(), 1)
    return out


def score(signals: dict, now: float) -> float:
    if not signals or "at" not in signals:
        return 0.0
    age = now - signals["at"]
    if age < -CLOCK_SKEW or age > PROXIMITY_TTL:
        return 0.0
    age = max(0.0, age)
    raw = sum(signals.get(key, 0.0) * weight for key, weight in PROXIMITY_WEIGHTS.items())
    if signals.get("screen_on", 0.0) >= 0.5:
        raw = min(1.0, raw + 0.05)
    return raw * 0.5 ** (age / HALF_LIFE)


def nearest(nodes: list[dict], now: float | None = None) -> dict:
    moment = now if now is not None else time.time()
    ranked = sorted(
        ((score(node.get("proximity") or {}, moment), node["id"]) for node in nodes if node.get("online")),
        reverse=True,
    )
    scores = {node_id: round(value, 3) for value, node_id in ranked}
    if not ranked or ranked[0][0] < PROXIMITY_FLOOR:
        return {"node_id": None, "confidence": 0.0, "scores": scores}
    best = ranked[0][0]
    second = ranked[1][0] if len(ranked) > 1 else 0.0
    if best - second < MARGIN:
        return {"node_id": None, "confidence": round(best, 3), "scores": scores, "ambiguous": True}
    return {"node_id": ranked[0][1], "confidence": round(min(1.0, best - second + best / 2), 3), "scores": scores}
