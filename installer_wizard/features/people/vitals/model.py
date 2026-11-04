import math
import time

HOUR, DAY = 3600, 86400

METRICS = {
    "heart_rate": {"min": 25, "max": 230, "unit": "bpm", "digits": 0, "fresh": 300, "max_age": HOUR, "group": "heart"},
    "resting_hr": {"min": 25, "max": 150, "unit": "bpm", "digits": 0, "fresh": DAY, "max_age": 2 * DAY, "group": "heart"},
    "hrv": {"min": 1, "max": 400, "unit": "ms", "digits": 0, "fresh": 12 * HOUR, "max_age": 2 * DAY, "group": "heart"},
    "spo2": {"min": 70, "max": 100, "unit": "%", "digits": 0, "fresh": 6 * HOUR, "max_age": DAY, "group": "breath"},
    "resp_rate": {"min": 4, "max": 60, "unit": "/min", "digits": 0, "fresh": 12 * HOUR, "max_age": 2 * DAY, "group": "breath"},
    "body_temp": {"min": 30, "max": 43, "unit": "°C", "digits": 1, "fresh": 6 * HOUR, "max_age": DAY, "group": "body"},
    "skin_temp": {"min": 20, "max": 42, "unit": "°C", "digits": 1, "fresh": HOUR, "max_age": DAY, "group": "body"},
    "bp_sys": {"min": 60, "max": 260, "unit": "mmHg", "digits": 0, "fresh": 3 * DAY, "max_age": 7 * DAY, "group": "body"},
    "bp_dia": {"min": 30, "max": 160, "unit": "mmHg", "digits": 0, "fresh": 3 * DAY, "max_age": 7 * DAY, "group": "body"},
    "glucose": {"min": 20, "max": 600, "unit": "mg/dL", "digits": 0, "fresh": 6 * HOUR, "max_age": 2 * DAY, "group": "body"},
    "weight": {"min": 2, "max": 400, "unit": "kg", "digits": 1, "fresh": 30 * DAY, "max_age": 60 * DAY, "group": "body"},
    "body_fat": {"min": 2, "max": 75, "unit": "%", "digits": 1, "fresh": 30 * DAY, "max_age": 60 * DAY, "group": "body"},
    "vo2max": {"min": 10, "max": 95, "unit": "ml/kg·min", "digits": 1, "fresh": 30 * DAY, "max_age": 90 * DAY, "group": "heart"},
    "steps": {"min": 0, "max": 150000, "unit": "", "digits": 0, "fresh": DAY, "max_age": 2 * DAY, "group": "move", "daily": True},
    "active_kcal": {"min": 0, "max": 20000, "unit": "kcal", "digits": 0, "fresh": DAY, "max_age": 2 * DAY, "group": "move", "daily": True},
    "distance_km": {"min": 0, "max": 500, "unit": "km", "digits": 2, "fresh": DAY, "max_age": 2 * DAY, "group": "move", "daily": True},
    "floors": {"min": 0, "max": 2000, "unit": "", "digits": 0, "fresh": DAY, "max_age": 2 * DAY, "group": "move", "daily": True},
    "sleep_min": {"min": 0, "max": 1440, "unit": "min", "digits": 0, "fresh": 20 * HOUR, "max_age": 2 * DAY, "group": "rest", "daily": True},
    "sleep_deep_min": {"min": 0, "max": 1440, "unit": "min", "digits": 0, "fresh": 20 * HOUR, "max_age": 2 * DAY, "group": "rest", "daily": True},
    "sleep_rem_min": {"min": 0, "max": 1440, "unit": "min", "digits": 0, "fresh": 20 * HOUR, "max_age": 2 * DAY, "group": "rest", "daily": True},
}
GROUPS = ("heart", "breath", "body", "move", "rest")
KINDS = ("ble", "push", "phone")
PRIORITY = {"camera": 0, "cloud": 1, "ble": 2, "push": 3, "phone": 4}
MAX_FUTURE = 60
MAX_AGE = max(spec["max_age"] for spec in METRICS.values())


def clean_sample(raw, now: float | None = None) -> dict:
    now = now or time.time()
    if not isinstance(raw, dict):
        raise ValueError("campione non valido")
    metric = str(raw.get("metric", ""))
    spec = METRICS.get(metric)
    if spec is None:
        raise ValueError("misura sconosciuta")
    value = raw.get("value")
    if isinstance(value, bool):
        raise ValueError("valore non numerico")
    try:
        value = float(value)
    except (TypeError, ValueError):
        raise ValueError("valore non numerico")
    if not math.isfinite(value) or not spec["min"] <= value <= spec["max"]:
        raise ValueError("valore fuori dai limiti")
    try:
        ts = float(raw.get("ts", now))
    except (TypeError, ValueError):
        raise ValueError("istante non valido")
    if not math.isfinite(ts) or ts > now + MAX_FUTURE or ts < now - spec["max_age"]:
        raise ValueError("istante fuori dai limiti")
    return {"metric": metric, "value": round(value, spec["digits"]) if spec["digits"] else int(round(value)), "ts": min(ts, now)}
