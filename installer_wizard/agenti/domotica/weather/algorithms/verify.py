from agenti.weather.algorithms.rounding import finite, round_to

TEMP_SPAN = 5.0
WIND_SPAN = 20.0
WET_MM = 0.2


def _mean(total: float, count: int) -> float | None:
    return total / count if count else None


def _tally() -> dict:
    return {"pairs": 0, "temp_n": 0, "temp_abs": 0.0, "temp_sum": 0.0, "rain_n": 0, "rain_hits": 0, "wind_n": 0, "wind_abs": 0.0}


def _add(t: dict, forecast: dict, seen: dict) -> None:
    used = False
    f, o = finite(forecast.get("temp")), finite(seen.get("temp"))
    if f is not None and o is not None:
        t["temp_n"] += 1
        t["temp_abs"] += abs(f - o)
        t["temp_sum"] += f - o
        used = True
    f, o = finite(forecast.get("rain")), finite(seen.get("rain"))
    if f is not None and o is not None:
        t["rain_n"] += 1
        t["rain_hits"] += int((f >= WET_MM) == (o >= WET_MM))
        used = True
    f, o = finite(forecast.get("wind")), finite(seen.get("wind"))
    if f is not None and o is not None:
        t["wind_n"] += 1
        t["wind_abs"] += abs(f - o)
        used = True
    if used:
        t["pairs"] += 1


def _score(model: str, t: dict) -> dict:
    temp_mae, temp_bias = _mean(t["temp_abs"], t["temp_n"]), _mean(t["temp_sum"], t["temp_n"])
    rain = t["rain_hits"] / t["rain_n"] if t["rain_n"] else None
    wind_mae = _mean(t["wind_abs"], t["wind_n"])
    total = weight = 0.0
    if temp_mae is not None:
        total += 0.5 * max(1.0 - temp_mae / TEMP_SPAN, 0.0)
        weight += 0.5
    if rain is not None:
        total += 0.3 * rain
        weight += 0.3
    if wind_mae is not None:
        total += 0.2 * max(1.0 - wind_mae / WIND_SPAN, 0.0)
        weight += 0.2
    score = total / weight if weight > 0 else 0.0
    shown = lambda value, digits: None if value is None else round_to(value, digits)
    return {"model": model, "pairs": t["pairs"], "temp_mae": shown(temp_mae, 3), "temp_bias": shown(temp_bias, 3),
            "rain_accuracy": shown(rain, 4), "wind_mae": shown(wind_mae, 3), "score": round_to(score, 4)}


def verify(forecasts: list[dict], observed: list[dict], lead: int | None = None, min_pairs: int = 0) -> dict:
    truth = {}
    for seen in observed:
        truth[str(seen["time"])] = seen
    tallies: dict[str, dict] = {}
    for forecast in forecasts:
        if lead is not None and int(forecast["lead"]) != lead:
            continue
        seen = truth.get(str(forecast["time"]))
        if seen is not None:
            _add(tallies.setdefault(str(forecast["model"]), _tally()), forecast, seen)
    models = [_score(name, t) for name, t in sorted(tallies.items()) if t["pairs"] > 0]
    models.sort(key=lambda m: m["model"])
    models.sort(key=lambda m: (-m["score"], -m["pairs"]))
    best = next((m["model"] for m in models if m["pairs"] >= max(min_pairs, 1)), None)
    return {"models": models, "best": best}
