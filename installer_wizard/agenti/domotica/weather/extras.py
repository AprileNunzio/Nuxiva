import math
from datetime import date

NOWCAST_SLOTS = 8
AIR_DAYS = 4
POLLEN = ("alder", "birch", "grass", "mugwort", "olive", "ragweed")


def _value(series: dict, key: str, index: int):
    values = series.get(key) or []
    value = values[index] if 0 <= index < len(values) else None
    return None if value is None or (isinstance(value, float) and math.isnan(value)) else value


def nowcast(raw: dict | None, now_stamp: str) -> list[dict]:
    series = raw or {}
    minute = int(now_stamp[14:16]) if len(now_stamp) >= 16 and now_stamp[14:16].isdigit() else 0
    floor = f"{now_stamp[:14]}{minute - minute % 15:02d}"
    out = []
    for index, stamp in enumerate(series.get("time") or []):
        if stamp[:16] < floor:
            continue
        rain = _value(series, "precipitation", index)
        out.append({"time": stamp, "rain": None if rain is None else round(float(rain), 2)})
        if len(out) >= NOWCAST_SLOTS:
            break
    return out


def yesterday(daily: dict, hourly: dict, start: int) -> dict | None:
    if not daily.get("time"):
        return None
    tmax, tmin = _value(daily, "temperature_2m_max", 0), _value(daily, "temperature_2m_min", 0)
    if tmax is None or tmin is None:
        return None
    same = _value(hourly, "temperature_2m", start - 24) if start >= 24 else None
    return {"iso": daily["time"][0], "tmax": round(float(tmax)), "tmin": round(float(tmin)),
            "rain_sum": _value(daily, "precipitation_sum", 0), "same_hour": None if same is None else round(float(same), 1)}


def air_days(raw: dict | None) -> list[dict]:
    series = (raw or {}).get("hourly") or {}
    by_day: dict[str, dict] = {}
    for index, stamp in enumerate(series.get("time") or []):
        day = by_day.setdefault(stamp[:10], {"iso": stamp[:10], "aqi": None, "pm25": None, "pollen": {}})
        for key, field in (("european_aqi", "aqi"), ("pm2_5", "pm25")):
            value = _value(series, key, index)
            if value is not None and (day[field] is None or value > day[field]):
                day[field] = round(float(value), 1)
        for name in POLLEN:
            value = _value(series, f"{name}_pollen", index)
            if value is not None and value > day["pollen"].get(name, -1):
                day["pollen"][name] = round(float(value), 1)
    today = date.today().isoformat()
    return [d for d in sorted(by_day.values(), key=lambda d: d["iso"]) if d["iso"] >= today][:AIR_DAYS]
