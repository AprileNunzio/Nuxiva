import logging
import math
import time
from datetime import date, datetime

import httpx

from features.weather import astro, settings
from features.weather.codes import DAYS_IT, MONTHS_IT, compass, describe

log = logging.getLogger("nuxiva.weather")
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
AIR_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"
STALE_SECONDS = 3 * 3600
CURRENT = ("temperature_2m,relative_humidity_2m,apparent_temperature,is_day,precipitation,weather_code,cloud_cover,"
           "pressure_msl,wind_speed_10m,wind_direction_10m,wind_gusts_10m")
HOURLY = ("temperature_2m,apparent_temperature,relative_humidity_2m,dew_point_2m,precipitation_probability,precipitation,"
          "weather_code,cloud_cover,visibility,wind_speed_10m,wind_gusts_10m,wind_direction_10m,uv_index,pressure_msl,is_day")
DAILY = ("weather_code,temperature_2m_max,temperature_2m_min,apparent_temperature_max,apparent_temperature_min,sunrise,sunset,"
         "daylight_duration,sunshine_duration,uv_index_max,precipitation_sum,snowfall_sum,precipitation_hours,"
         "precipitation_probability_max,wind_speed_10m_max,wind_gusts_10m_max,wind_direction_10m_dominant")
AIR_CURRENT = ("european_aqi,us_aqi,pm10,pm2_5,carbon_monoxide,nitrogen_dioxide,sulphur_dioxide,ozone,dust,"
               "alder_pollen,birch_pollen,grass_pollen,mugwort_pollen,olive_pollen,ragweed_pollen")
POLLEN = ("alder", "birch", "grass", "mugwort", "olive", "ragweed")
AQI_BANDS = ((20, "good"), (40, "fair"), (60, "moderate"), (80, "poor"), (100, "very_poor"), (10_000, "extreme"))
POLLEN_BANDS = ((10, "low"), (50, "moderate"), (200, "high"), (10_000, "very_high"))
cache: dict[tuple, tuple[float, dict]] = {}


class WeatherUnavailable(RuntimeError):
    pass


def at(series: dict, key: str, index: int):
    values = series.get(key) or []
    return values[index] if 0 <= index < len(values) else None


def rounded(value, digits: int = 0):
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return None
    return round(value) if digits == 0 else round(value, digits)


def band(value, bands) -> str:
    if value is None:
        return ""
    return next(name for limit, name in bands if value <= limit)


def hourly_rows(hourly: dict, start: int, count: int) -> list[dict]:
    rows = []
    for index in range(start, min(start + count, len(hourly.get("time") or []))):
        code = at(hourly, "weather_code", index)
        daytime = bool(at(hourly, "is_day", index))
        desc, icon = describe(code, not daytime)
        visibility = at(hourly, "visibility", index)
        rows.append({"time": hourly["time"][index], "temp": rounded(at(hourly, "temperature_2m", index), 1),
                     "feels": rounded(at(hourly, "apparent_temperature", index), 1), "humidity": at(hourly, "relative_humidity_2m", index),
                     "dew": rounded(at(hourly, "dew_point_2m", index), 1), "rain_prob": at(hourly, "precipitation_probability", index),
                     "rain": rounded(at(hourly, "precipitation", index), 1), "code": code, "icon": icon, "desc": desc, "day": daytime,
                     "cloud": at(hourly, "cloud_cover", index), "visibility": rounded(visibility / 1000, 1) if visibility is not None else None,
                     "wind": rounded(at(hourly, "wind_speed_10m", index)), "gust": rounded(at(hourly, "wind_gusts_10m", index)),
                     "dir": at(hourly, "wind_direction_10m", index), "uv": rounded(at(hourly, "uv_index", index), 1),
                     "pressure": rounded(at(hourly, "pressure_msl", index))})
    return rows


def daily_rows(daily: dict) -> list[dict]:
    rows = []
    for index, day in enumerate(daily.get("time") or []):
        stamp = date.fromisoformat(day)
        desc, icon = describe(at(daily, "weather_code", index))
        sunrise, sunset = at(daily, "sunrise", index) or "", at(daily, "sunset", index) or ""
        rows.append({"label": "Oggi" if index == 0 else ("Domani" if index == 1 else DAYS_IT[stamp.weekday()]),
                     "iso": day, "weekday": stamp.weekday(), "date": f"{stamp.day} {MONTHS_IT[stamp.month - 1]}", "desc": desc, "icon": icon,
                     "code": at(daily, "weather_code", index), "tmax": rounded(at(daily, "temperature_2m_max", index)),
                     "tmin": rounded(at(daily, "temperature_2m_min", index)), "feels_max": rounded(at(daily, "apparent_temperature_max", index)),
                     "feels_min": rounded(at(daily, "apparent_temperature_min", index)), "rain": at(daily, "precipitation_probability_max", index),
                     "rain_sum": rounded(at(daily, "precipitation_sum", index), 1), "snow_sum": rounded(at(daily, "snowfall_sum", index), 1),
                     "rain_hours": rounded(at(daily, "precipitation_hours", index)), "wind": rounded(at(daily, "wind_speed_10m_max", index)),
                     "gust": rounded(at(daily, "wind_gusts_10m_max", index)), "dir": at(daily, "wind_direction_10m_dominant", index),
                     "dir_name": compass(at(daily, "wind_direction_10m_dominant", index)), "uv": rounded(at(daily, "uv_index_max", index), 1),
                     "sunrise": sunrise[-5:], "sunset": sunset[-5:], "daylight_min": rounded((at(daily, "daylight_duration", index) or 0) / 60),
                     "sun_min": rounded((at(daily, "sunshine_duration", index) or 0) / 60)})
    return rows


def pressure_trend(hourly: dict, index: int) -> str:
    before, now = at(hourly, "pressure_msl", max(0, index - 3)), at(hourly, "pressure_msl", index)
    if before is None or now is None:
        return ""
    return "rising" if now - before > 1 else "falling" if before - now > 1 else "steady"


def air_block(raw: dict | None) -> dict | None:
    current = (raw or {}).get("current")
    if not current:
        return None
    european, us = current.get("european_aqi"), current.get("us_aqi")
    pollen = {name: {"value": rounded(current.get(f"{name}_pollen")), "level": band(current.get(f"{name}_pollen"), POLLEN_BANDS)}
              for name in POLLEN if current.get(f"{name}_pollen") is not None}
    return {"aqi": european, "us_aqi": us, "level": band(european, AQI_BANDS), "pm25": rounded(current.get("pm2_5"), 1),
            "pm10": rounded(current.get("pm10"), 1), "no2": rounded(current.get("nitrogen_dioxide"), 1), "so2": rounded(current.get("sulphur_dioxide"), 1),
            "o3": rounded(current.get("ozone"), 1), "co": rounded(current.get("carbon_monoxide")), "dust": rounded(current.get("dust"), 1), "pollen": pollen}


def build(place: dict, forecast: dict, air: dict | None, hours: int) -> dict:
    now, hourly = forecast["current"], forecast["hourly"]
    stamp = now["time"][:13]
    start = next((i for i, value in enumerate(hourly["time"]) if value[:13] >= stamp), 0)
    daytime = bool(now.get("is_day"))
    desc, icon = describe(now.get("weather_code"), not daytime)
    rows = hourly_rows(hourly, start, hours)
    days = daily_rows(forecast["daily"])
    here = rows[0] if rows else {}
    current = {"temp": rounded(now["temperature_2m"]), "temp_exact": rounded(now["temperature_2m"], 1), "feels": rounded(now["apparent_temperature"]),
               "humidity": now["relative_humidity_2m"], "wind": rounded(now["wind_speed_10m"]), "gust": rounded(now.get("wind_gusts_10m")),
               "dir": now.get("wind_direction_10m"), "dir_name": compass(now.get("wind_direction_10m")), "desc": desc, "icon": icon,
               "code": now.get("weather_code"), "day": daytime, "pressure": rounded(now.get("pressure_msl")),
               "pressure_trend": pressure_trend(hourly, start), "cloud": now.get("cloud_cover"), "rain_now": rounded(now.get("precipitation"), 1),
               "dew": here.get("dew"), "visibility": here.get("visibility"), "uv": here.get("uv"), "time": now["time"]}
    payload = {"location": place["name"], "detail": place.get("detail", ""), "lat": place["lat"], "lon": place["lon"],
               "timezone": forecast.get("timezone", ""), "elevation": forecast.get("elevation"), "current": current, "hourly": rows,
               "days": days, "air": air_block(air), "fetched": time.time(), "source": "open-meteo.com"}
    return payload


async def fetch(place: dict, days: int, hours: int, with_air: bool, refresh_minutes: int) -> dict:
    key = (round(place["lat"], 2), round(place["lon"], 2), days, hours, with_air)
    hit = cache.get(key)
    if hit and time.time() - hit[0] < refresh_minutes * 60:
        return {**hit[1], "location": place["name"], "detail": place.get("detail", "")}
    try:
        async with httpx.AsyncClient(timeout=12) as client:
            forecast_task = client.get(FORECAST_URL, params={"latitude": place["lat"], "longitude": place["lon"], "timezone": "auto",
                                                              "forecast_days": days, "forecast_hours": 72, "past_hours": 3, "current": CURRENT,
                                                              "hourly": HOURLY, "daily": DAILY})
            air = None
            if with_air:
                try:
                    air = (await client.get(AIR_URL, params={"latitude": place["lat"], "longitude": place["lon"], "timezone": "auto",
                                                              "current": AIR_CURRENT})).json()
                except (httpx.HTTPError, ValueError) as exc:
                    log.info("Qualità dell'aria non disponibile: %s", type(exc).__name__)
            response = await forecast_task
            response.raise_for_status()
            payload = build(place, response.json(), air, hours)
    except (httpx.HTTPError, ValueError, KeyError) as exc:
        if hit and time.time() - hit[0] < STALE_SECONDS:
            return {**hit[1], "stale": True}
        raise WeatherUnavailable(type(exc).__name__) from exc
    cache[key] = (time.time(), payload)
    return payload


async def report(place: dict) -> dict:
    prefs = settings.current()
    payload = await fetch(place, prefs["days"], prefs["hours"], prefs["air"], prefs["refresh"])
    result = {**payload, "units": prefs["units"], "view": prefs["view"]}
    if not prefs["air"]:
        result["air"] = None
    elif not prefs["pollen"] and result.get("air"):
        result["air"] = {**result["air"], "pollen": {}}
    result["astro"] = astro.moon(datetime.now().astimezone()) if prefs["astro"] else None
    return result
