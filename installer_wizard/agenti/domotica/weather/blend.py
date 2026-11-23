import math

CORE_CURRENT = "temperature_2m,apparent_temperature,precipitation,weather_code,wind_speed_10m,wind_direction_10m"
CORE_HOURLY = "temperature_2m,apparent_temperature,precipitation,weather_code,wind_speed_10m,wind_direction_10m"
CORE_DAILY = "weather_code,temperature_2m_max,temperature_2m_min,precipitation_sum,wind_speed_10m_max"


def _usable(value) -> bool:
    return value is not None and not (isinstance(value, float) and math.isnan(value))


def params(base: dict, model: str) -> dict:
    keep = {k: v for k, v in base.items() if k not in ("current", "hourly", "daily", "minutely_15", "forecast_minutely_15")}
    return {**keep, "current": CORE_CURRENT, "hourly": CORE_HOURLY, "daily": CORE_DAILY, "models": model}


def _series(base: dict, extra: dict) -> int:
    times, other = base.get("time") or [], extra.get("time") or []
    where = {stamp: index for index, stamp in enumerate(other)}
    replaced = 0
    for key, values in extra.items():
        if key == "time" or not isinstance(values, list) or not isinstance(base.get(key), list):
            continue
        target = base[key]
        for index, stamp in enumerate(times):
            source = where.get(stamp)
            if source is None or source >= len(values) or index >= len(target) or not _usable(values[source]):
                continue
            target[index] = values[source]
            replaced += 1
    return replaced


def _current(base: dict, extra: dict) -> int:
    if not base or not extra or base.get("time") != extra.get("time"):
        return 0
    replaced = 0
    for key, value in extra.items():
        if key in ("time", "interval") or key not in base or not _usable(value):
            continue
        base[key] = value
        replaced += 1
    return replaced


def merge(forecast: dict, model: dict | None) -> tuple[dict, bool]:
    if not isinstance(model, dict):
        return forecast, False
    merged = {**forecast, **{k: dict(forecast.get(k) or {}) for k in ("current", "hourly", "daily")}}
    for section in ("hourly", "daily"):
        merged[section] = {k: (list(v) if isinstance(v, list) else v) for k, v in merged[section].items()}
    replaced = _current(merged["current"], model.get("current") or {})
    for section in ("hourly", "daily"):
        replaced += _series(merged[section], model.get(section) or {})
    return merged, replaced > 0
