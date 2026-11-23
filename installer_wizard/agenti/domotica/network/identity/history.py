MAX_IPS = 10
MAX_MACS = 10
KEEP = ("name", "room", "owner", "notes", "hostname", "vendor", "os", "web_title")


def _push(items: list, value, limit: int) -> list:
    if not value:
        return items
    out = [v for v in items if v != value] + [value]
    return out[-limit:]


def remember(device: dict, previous_ip: str | None, mac: str | None) -> None:
    ips = device.get("ips") if isinstance(device.get("ips"), list) else []
    ips = _push(ips, previous_ip, MAX_IPS)
    device["ips"] = _push(ips, device.get("ip"), MAX_IPS)
    macs = device.get("macs") if isinstance(device.get("macs"), list) else []
    device["macs"] = _push(macs, mac, MAX_MACS)


def absorb(device: dict, old: dict) -> None:
    if not old:
        return
    for field in KEEP:
        if not device.get(field) and old.get(field):
            device[field] = old[field]
    device["trusted"] = bool(device.get("trusted") or old.get("trusted"))
    device["first_seen"] = min(device.get("first_seen") or old.get("first_seen") or 0, old.get("first_seen") or device.get("first_seen") or 0)
    device["sessions"] = sorted((old.get("sessions") or []) + (device.get("sessions") or []))[-300:]
    if not device.get("ports") and old.get("ports"):
        device["ports"], device["studied"] = old["ports"], old.get("studied", 0)
    for ip in old.get("ips") or ([old["ip"]] if old.get("ip") else []):
        device["ips"] = _push(device.get("ips") or [], ip, MAX_IPS)
