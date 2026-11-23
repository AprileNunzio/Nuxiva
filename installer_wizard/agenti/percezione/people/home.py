FACE_WINDOW = 600
PHONE_TYPES = ("phone", "computer")


def _owner_keys(profile: dict, display: str) -> set[str]:
    return {v.strip().casefold() for v in (profile.get("slug"), display, profile.get("first_name"), profile.get("nickname")) if isinstance(v, str) and v.strip()}


def network_devices() -> list[dict]:
    from agenti.network.explorer import explorer
    return [d for d in explorer.devices.values() if isinstance(d, dict)]


def status(profile: dict, display: str, visible: set, now: float, devices: list[dict]) -> dict:
    seen = float((profile.get("stats") or {}).get("last_seen") or 0)
    if profile.get("slug") in visible:
        return {"home": True, "via": "camera", "seen": now}
    keys = _owner_keys(profile, display)
    owned = [d for d in devices if str(d.get("owner", "")).strip().casefold() in keys and d.get("type") in PHONE_TYPES]
    if any(d.get("online") for d in owned):
        return {"home": True, "via": "wifi", "seen": max([seen, *(float(d.get("last_seen") or 0) for d in owned)])}
    if seen and now - seen <= FACE_WINDOW:
        return {"home": True, "via": "recent", "seen": seen}
    return {"home": False, "via": "", "seen": seen or None}
