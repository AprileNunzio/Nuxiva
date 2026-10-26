import math
import time

METRICS = {
    "heart_rate": {"min": 30, "max": 220, "unit": "bpm", "digits": 0},
    "spo2": {"min": 70, "max": 100, "unit": "%", "digits": 0},
    "body_temp": {"min": 30, "max": 43, "unit": "°C", "digits": 1},
    "skin_temp": {"min": 20, "max": 42, "unit": "°C", "digits": 1},
    "resp_rate": {"min": 4, "max": 60, "unit": "/min", "digits": 0},
    "hrv": {"min": 1, "max": 400, "unit": "ms", "digits": 0},
}
KINDS = ("ble", "push", "phone")
PRIORITY = {"cloud": 1, "ble": 2, "push": 3, "phone": 4}
MAX_FUTURE = 60
MAX_AGE = 3600


def clean_sample(raw, now: float | None = None) -> dict:
    now = now or time.time()
    if not isinstance(raw, dict):
        raise ValueError("campione non valido")
    metric = str(raw.get("metric", ""))
    spec = METRICS.get(metric)
    if spec is None:
        raise ValueError("misura sconosciuta")
    try:
        value = float(raw.get("value"))
    except (TypeError, ValueError):
        raise ValueError("valore non numerico")
    if not math.isfinite(value) or not spec["min"] <= value <= spec["max"]:
        raise ValueError("valore fuori dai limiti")
    try:
        ts = float(raw.get("ts", now))
    except (TypeError, ValueError):
        raise ValueError("istante non valido")
    if not math.isfinite(ts) or ts > now + MAX_FUTURE or ts < now - MAX_AGE:
        raise ValueError("istante fuori dai limiti")
    return {"metric": metric, "value": round(value, spec["digits"]) if spec["digits"] else int(round(value)), "ts": ts}
