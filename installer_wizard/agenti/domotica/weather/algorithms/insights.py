import math

from agenti.weather.algorithms.rounding import finite, round_to

NEAR_HOURS = 12
DAY_HOURS = 24
WET_MM = 0.1
STORM = (95, 96, 99)
SNOW = (71, 73, 75, 77, 85, 86, 66)
FOG = (45, 48)
LEVELS = {"info": 0, "warn": 1, "alert": 2}


def _item(kind: str, level: str, value=None, time=None) -> dict:
    out = {"kind": kind, "level": level}
    if value is not None:
        out["value"] = value
    if time is not None:
        out["time"] = time
    return out


def _peak(hours: list[dict], key: str):
    best = None
    for hour in hours:
        value = finite(hour.get(key))
        if value is not None and (best is None or value > best[0]):
            best = (value, hour["time"])
    return best


def _first_code(hours: list[dict], codes: tuple) -> str | None:
    for hour in hours:
        code = hour.get("code")
        if isinstance(code, int) and not isinstance(code, bool) and code in codes:
            return hour["time"]
    return None


def _yesterday(out: list, situation: dict) -> None:
    days, before = situation.get("days") or [], situation.get("yesterday") or {}
    now, then = finite(days[0].get("tmax")) if days else None, finite(before.get("tmax"))
    if now is None or then is None:
        return
    delta = round_to(now - then, 1)
    out.append(_item("warmer" if delta >= 1.0 else "colder" if delta <= -1.0 else "same", "info", delta))


def _nowcast(out: list, slots: list[dict]) -> None:
    wet = lambda s: (finite(s.get("rain")) or 0.0) >= WET_MM
    if not slots:
        return
    if wet(slots[0]):
        dry = next((s for s in slots if not wet(s) and finite(s.get("rain")) is not None), None)
        out.append(_item("rain_stops", "info", None, dry["time"]) if dry else _item("raining", "info"))
        return
    start = next((s for s in slots if wet(s)), None)
    if start:
        total = 0.0
        for s in slots:
            value = finite(s.get("rain"))
            if value is not None:
                total += value
        out.append(_item("rain_soon", "warn", round_to(total, 1), start["time"]))


def insights(situation: dict) -> list[dict]:
    out: list[dict] = []
    hourly = situation.get("hourly") or []
    day, near = hourly[:DAY_HOURS], hourly[:NEAR_HOURS]
    days = situation.get("days") or []
    _yesterday(out, situation)
    _nowcast(out, situation.get("nowcast") or [])
    if (time := _first_code(day, STORM)) is not None:
        out.append(_item("storm", "alert", None, time))
    if (time := _first_code(day, SNOW)) is not None:
        out.append(_item("snow", "warn", None, time))
    if (peak := _peak(near, "rain_prob")) and peak[0] >= 50.0:
        out.append(_item("umbrella", "warn" if peak[0] >= 80.0 else "info", peak[0], peak[1]))
    if (peak := _peak(day, "gust")) and peak[0] >= 50.0:
        out.append(_item("wind", "alert" if peak[0] >= 75.0 else "warn", round_to(peak[0], 0), peak[1]))
    if (peak := _peak(day, "feels")) and peak[0] >= 32.0:
        out.append(_item("heat", "alert" if peak[0] >= 38.0 else "warn", round_to(peak[0], 0), peak[1]))
    low = math.inf
    for d in days[:2]:
        value = finite(d.get("tmin"))
        if value is not None:
            low = min(low, value)
    if math.isfinite(low) and low <= 1.0:
        out.append(_item("frost", "alert" if low <= -5.0 else "warn", round_to(low, 0)))
    uv = finite(days[0].get("uv")) if days else None
    if uv is not None and uv >= 6.0:
        out.append(_item("uv", "alert" if uv >= 8.0 else "warn", round_to(uv, 1)))
    if (time := _first_code(near, FOG)) is not None:
        out.append(_item("fog", "info", None, time))
    out.sort(key=lambda item: -LEVELS[item["level"]])
    return out
