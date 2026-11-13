import json
import re
import threading
import time
from datetime import date, datetime

import httpx

from config import STATE_DIR
from sealed import write_private

from agenti.weather.algorithms import engine

FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
MODELS = ("ecmwf_ifs025", "icon_seamless", "gfs_seamless", "meteofrance_seamless")
HOURLY = "temperature_2m,precipitation,wind_speed_10m"
ROOT = STATE_DIR / "weather" / "skill"
MAX_LEAD = 10
STEP_HOURS = 3
KEEP_DAYS = 15
MAX_FORECASTS = 40_000
MIN_PAIRS = 16
KEY_RE = re.compile(r"^-?\d{1,3}\.\d{2}_-?\d{1,3}\.\d{2}$")
lock = threading.RLock()


class SkillUnavailable(RuntimeError):
    pass


def key(place: dict) -> str:
    value = f"{float(place['lat']):.2f}_{float(place['lon']):.2f}"
    if not KEY_RE.fullmatch(value):
        raise ValueError("località non valida")
    return value


def _file(place: dict):
    return ROOT / f"{key(place)}.json"


def load(place: dict) -> dict:
    try:
        data = json.loads(_file(place).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        data = {}
    if not isinstance(data, dict):
        data = {}
    forecasts = [f for f in data.get("forecasts", []) if isinstance(f, dict)] if isinstance(data.get("forecasts"), list) else []
    observed = data.get("observed") if isinstance(data.get("observed"), dict) else {}
    choice = data.get("choice") if isinstance(data.get("choice"), dict) else {}
    return {"forecasts": forecasts[-MAX_FORECASTS:], "observed": observed, "choice": choice}


def _save(place: dict, data: dict) -> None:
    ROOT.mkdir(parents=True, exist_ok=True)
    write_private(_file(place), json.dumps(data, ensure_ascii=False, separators=(",", ":")).encode())


def _number(series: dict, name: str, index: int):
    values = series.get(name) or []
    value = values[index] if 0 <= index < len(values) else None
    return float(value) if isinstance(value, (int, float)) and not isinstance(value, bool) else None


def record(data: dict, models_hourly: dict, observed_hourly: dict, today: date, now_hour: str) -> dict:
    seen = {(f.get("model"), f.get("lead"), f.get("time")) for f in data["forecasts"]}
    for index, stamp in enumerate(models_hourly.get("time") or []):
        if int(stamp[11:13]) % STEP_HOURS:
            continue
        lead = (date.fromisoformat(stamp[:10]) - today).days
        if not 1 <= lead <= MAX_LEAD:
            continue
        for model in MODELS:
            item = {"model": model, "lead": lead, "time": stamp, "temp": _number(models_hourly, f"temperature_2m_{model}", index),
                    "rain": _number(models_hourly, f"precipitation_{model}", index), "wind": _number(models_hourly, f"wind_speed_10m_{model}", index)}
            if item["temp"] is None or (model, lead, stamp) in seen:
                continue
            seen.add((model, lead, stamp))
            data["forecasts"].append(item)
    for index, stamp in enumerate(observed_hourly.get("time") or []):
        if stamp < now_hour and not int(stamp[11:13]) % STEP_HOURS:
            data["observed"][stamp] = {"temp": _number(observed_hourly, "temperature_2m", index),
                                       "rain": _number(observed_hourly, "precipitation", index),
                                       "wind": _number(observed_hourly, "wind_speed_10m", index)}
    oldest = date.fromordinal(today.toordinal() - KEEP_DAYS).isoformat()
    data["observed"] = {t: v for t, v in sorted(data["observed"].items()) if t >= oldest}
    data["forecasts"] = [f for f in data["forecasts"] if str(f.get("time", "")) >= oldest][-MAX_FORECASTS:]
    return data


def judge(data: dict) -> dict:
    observed = [{"time": t, **v} for t, v in data["observed"].items() if isinstance(v, dict)]
    leads = {}
    for lead in range(1, MAX_LEAD + 1):
        verdict = engine.verify(data["forecasts"], observed, lead, MIN_PAIRS)
        leads[str(lead)] = {"best": verdict["best"], "models": verdict["models"][:len(MODELS)]}
    overall = engine.verify([f for f in data["forecasts"] if int(f.get("lead", 0)) <= 3], observed, None, MIN_PAIRS + 8)
    return {"model": overall["best"], "models": overall["models"][:len(MODELS)], "leads": leads, "updated": int(time.time())}


async def _fetch(place: dict) -> tuple[dict, dict]:
    base = {"latitude": place["lat"], "longitude": place["lon"], "timezone": "auto", "hourly": HOURLY}
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            models = await client.get(FORECAST_URL, params={**base, "models": ",".join(MODELS), "forecast_days": MAX_LEAD + 1})
            past = await client.get(FORECAST_URL, params={**base, "past_days": 2, "forecast_days": 1})
            models.raise_for_status()
            past.raise_for_status()
            return models.json().get("hourly") or {}, past.json().get("hourly") or {}
    except (httpx.HTTPError, ValueError) as exc:
        raise SkillUnavailable(type(exc).__name__) from exc


async def learn(place: dict) -> dict:
    models_hourly, observed_hourly = await _fetch(place)
    now = datetime.now().astimezone()
    with lock:
        data = record(load(place), models_hourly, observed_hourly, now.date(), now.strftime("%Y-%m-%dT%H:00"))
        data["choice"] = judge(data)
        _save(place, data)
    return data["choice"]


def preferred_model(place: dict) -> str | None:
    try:
        model = load(place)["choice"].get("model")
    except (ValueError, KeyError, TypeError):
        return None
    return model if model in MODELS else None


def standing(place: dict) -> dict:
    data = load(place)
    return {"choice": data["choice"], "forecasts": len(data["forecasts"]), "observed": len(data["observed"])}
