OK = "ok"
STALE = "stale"
UNAVAILABLE = "unavailable"
DISABLED = "disabled"
OUT_OF_SEASON = "out_of_season"
FALLBACK = "fallback"
POLLEN = ("alder", "birch", "grass", "mugwort", "olive", "ragweed")


def air_state(raw: dict | None, requested: bool) -> str:
    if not requested:
        return DISABLED
    return OK if isinstance(raw, dict) and isinstance(raw.get("current"), dict) else UNAVAILABLE


def pollen_state(raw: dict | None, air: str) -> str:
    if air != OK:
        return air
    current = raw.get("current") or {}
    hourly = raw.get("hourly") or {}
    now = any(current.get(f"{name}_pollen") is not None for name in POLLEN)
    ahead = any(v is not None for name in POLLEN for v in (hourly.get(f"{name}_pollen") or []))
    return OK if now or ahead else OUT_OF_SEASON


def model_state(model: str | None, used: bool) -> str:
    if not model:
        return DISABLED
    return OK if used else FALLBACK


def apply_preferences(result: dict, prefs: dict) -> dict:
    states = dict(result.get("sources") or {})
    if not prefs["air"]:
        result["air"], result["air_days"] = None, []
        states["air"], states["pollen"] = DISABLED, DISABLED
    elif not prefs["pollen"]:
        if result.get("air"):
            result["air"] = {**result["air"], "pollen": {}}
        result["air_days"] = [{**d, "pollen": {}} for d in result.get("air_days") or []]
        states["pollen"] = DISABLED
    result["sources"] = states
    return result
