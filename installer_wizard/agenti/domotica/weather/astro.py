import math
from datetime import datetime, timedelta, timezone

SYNODIC = 29.530588853
REFERENCE = datetime(2000, 1, 6, 18, 14, tzinfo=timezone.utc)
PHASES = ("new", "waxing_crescent", "first_quarter", "waxing_gibbous", "full", "waning_gibbous", "last_quarter", "waning_crescent")


def age(moment: datetime) -> float:
    return ((moment.astimezone(timezone.utc) - REFERENCE).total_seconds() / 86400) % SYNODIC


def moon(moment: datetime | None = None) -> dict:
    now = moment or datetime.now(timezone.utc)
    days = age(now)
    fraction = days / SYNODIC
    return {"phase": PHASES[int(fraction * 8 + 0.5) % 8], "age": round(days, 1), "fraction": round(fraction, 3),
            "illumination": round((1 - math.cos(2 * math.pi * fraction)) / 2 * 100),
            "next_new": (now + timedelta(days=SYNODIC - days)).date().isoformat(),
            "next_full": (now + timedelta(days=(SYNODIC / 2 - days) % SYNODIC)).date().isoformat()}
