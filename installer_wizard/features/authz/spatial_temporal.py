import time
from datetime import datetime
from features.authz.policy import Decision
from features.authz.principal import Principal
from features.authz.risk import Risk


def is_time_allowed(schedule_str: str, now: float | None = None) -> bool:
    if not schedule_str:
        return True
    current = datetime.fromtimestamp(now or time.time())
    current_minutes = current.hour * 60 + current.minute
    parts = schedule_str.split("-")
    if len(parts) != 2:
        return True
    try:
        sh, sm = map(int, parts[0].strip().split(":"))
        eh, em = map(int, parts[1].strip().split(":"))
        start_min = sh * 60 + sm
        end_min = eh * 60 + em
        if start_min <= end_min:
            return start_min <= current_minutes <= end_min
        return current_minutes >= start_min or current_minutes <= end_min
    except (ValueError, IndexError):
        return True


def is_zone_allowed(principal_zones: tuple[str, ...], device_zone: str) -> bool:
    if not principal_zones:
        return True
    if not device_zone:
        return True
    return device_zone.lower().strip() in (z.lower().strip() for z in principal_zones)


def validate_spatial_temporal(principal: Principal, device_zone: str = "", now: float | None = None) -> Decision | None:
    if principal.role in ("system", "owner"):
        return None
    if principal.zones and not is_zone_allowed(principal.zones, device_zone):
        return Decision(False, "zone", Risk.HOME)
    if principal.schedule and not is_time_allowed(principal.schedule, now):
        return Decision(False, "schedule", Risk.HOME)
    return None
