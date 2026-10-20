from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from typing import Callable, Dict

WINDOW_PATTERN = re.compile(r"^(?:[01]\d|2[0-3]):[0-5]\d$")
WINDOW_SPAN_MINUTES = 60
DEFAULT_WINDOW = "03:00"
MIN_INTERVAL = 1
MAX_INTERVAL = 1440


class PolicyError(ValueError):
    pass


@dataclass(frozen=True)
class UpdatePolicy:
    auto_update: bool
    window: str
    interval_minutes: int
    sync_nodes: bool
    require_ci: bool

    def as_dict(self) -> Dict[str, object]:
        return asdict(self)


def _flag(value: str, default: bool) -> bool:
    if value == "":
        return default
    return value.strip() not in {"0", "off", "no", "false"}


def _interval(value: str) -> int:
    try:
        return max(MIN_INTERVAL, min(MAX_INTERVAL, int(float(value))))
    except (TypeError, ValueError):
        return 5


def load_policy(reader: Callable[[str, str], str]) -> UpdatePolicy:
    window = window_value(reader("NUXIVA_UPDATE_WINDOW", DEFAULT_WINDOW))
    return UpdatePolicy(
        auto_update=_flag(reader("NUXIVA_AUTO_UPDATE", "1"), True),
        window=window if window == "" or WINDOW_PATTERN.match(window) else DEFAULT_WINDOW,
        interval_minutes=_interval(reader("NUXIVA_UPDATE_INTERVAL_MIN", "5")),
        sync_nodes=_flag(reader("NUXIVA_UPDATE_SYNC_NODES", "1"), True),
        require_ci=_flag(reader("NUXIVA_UPDATE_REQUIRE_CI", "1"), True),
    )


def policy_to_env(policy: UpdatePolicy) -> Dict[str, str]:
    if policy.window and not WINDOW_PATTERN.match(policy.window):
        raise PolicyError("invalid_window")
    if not MIN_INTERVAL <= policy.interval_minutes <= MAX_INTERVAL:
        raise PolicyError("invalid_interval")
    return {
        "NUXIVA_AUTO_UPDATE": "1" if policy.auto_update else "0",
        "NUXIVA_UPDATE_WINDOW": policy.window or "off",
        "NUXIVA_UPDATE_INTERVAL_MIN": str(policy.interval_minutes),
        "NUXIVA_UPDATE_SYNC_NODES": "1" if policy.sync_nodes else "0",
        "NUXIVA_UPDATE_REQUIRE_CI": "1" if policy.require_ci else "0",
    }


def window_value(raw: str) -> str:
    return "" if raw.strip().lower() == "off" else raw.strip()


def in_window(now: datetime, window: str, span_minutes: int = WINDOW_SPAN_MINUTES) -> bool:
    if not window:
        return True
    hours, minutes = (int(part) for part in window.split(":"))
    start = now.replace(hour=hours, minute=minutes, second=0, microsecond=0)
    if now < start:
        start -= timedelta(days=1)
    return now - start < timedelta(minutes=span_minutes)


def next_window(now: datetime, window: str) -> datetime | None:
    if not window:
        return None
    hours, minutes = (int(part) for part in window.split(":"))
    candidate = now.replace(hour=hours, minute=minutes, second=0, microsecond=0)
    return candidate if candidate > now else candidate + timedelta(days=1)
