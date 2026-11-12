RESTRICTED_ROLES = frozenset({"guest", "service"})
MAX_VALUES = 24


def may_read(profile: dict | None) -> bool:
    if not isinstance(profile, dict) or profile.get("consent") is False or profile.get("share_health") is False:
        return False
    role = profile.get("role") if isinstance(profile.get("role"), str) else ""
    return profile.get("share_health") is True if role in RESTRICTED_ROLES else True


def _rounded(value, digits: int):
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return round(number, digits) if digits else int(round(number))


def summary(view: dict, metrics: dict) -> dict:
    if not view:
        return {"available": False}
    values = {}
    for metric, row in sorted((view.get("values") or {}).items()):
        spec = metrics.get(metric)
        if not spec or not isinstance(row, dict) or len(values) >= MAX_VALUES:
            continue
        value = _rounded(row.get("value"), int(spec.get("digits", 0)))
        if value is not None:
            values[metric] = {"value": value, "unit": spec.get("unit", ""), "source": str(row.get("kind", ""))[:24]}
    recovery = view.get("recovery") or None
    return {
        "available": bool(values),
        "values": values,
        "recovery": {"score": recovery["score"], "band": recovery["band"]} if recovery else None,
        "signals": [{"metric": s["metric"], "code": s["code"], "level": s["level"]} for s in view.get("signals") or []],
        "sources": list(view.get("sources") or []),
    }
