from config import env_get

UNIT_SYSTEMS = ("metric", "imperial")
WIND_UNITS = ("auto", "kmh", "ms", "mph", "kn")
VIEWS = ("day", "week")
DAY_CHOICES = (5, 7, 10, 14)


def _pick(key: str, default: str, allowed: tuple) -> str:
    value = env_get(key, default).strip().lower()
    return value if value in allowed else default


def _number(key: str, default: int, low: int, high: int) -> int:
    try:
        return max(low, min(high, int(env_get(key, str(default)))))
    except ValueError:
        return default


def flag(key: str, default: bool) -> bool:
    return env_get(key, "1" if default else "0").strip().lower() not in ("0", "off", "no", "false")


def units() -> dict:
    system = _pick("NUXIVA_WEATHER_UNITS", "metric", UNIT_SYSTEMS)
    wind = _pick("NUXIVA_WEATHER_WIND", "auto", WIND_UNITS)
    if wind == "auto":
        wind = "mph" if system == "imperial" else "kmh"
    imperial = system == "imperial"
    return {"temp": "f" if imperial else "c", "wind": wind, "precip": "in" if imperial else "mm",
            "pressure": "inhg" if imperial else "hpa", "distance": "mi" if imperial else "km"}


def current() -> dict:
    return {"units": units(), "days": _pick_days(), "refresh": _number("NUXIVA_WEATHER_REFRESH", 10, 5, 120),
            "view": _pick("NUXIVA_WEATHER_VIEW", "day", VIEWS), "air": flag("NUXIVA_WEATHER_AIR", True),
            "pollen": flag("NUXIVA_WEATHER_POLLEN", True), "astro": flag("NUXIVA_WEATHER_ASTRO", True),
            "hours": _number("NUXIVA_WEATHER_HOURS", 24, 12, 48)}


def _pick_days() -> int:
    days = _number("NUXIVA_WEATHER_DAYS", 7, 3, 16)
    return days if days in DAY_CHOICES else 7
