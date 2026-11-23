import re

SELF_KEY = "self"
_HEX = re.compile(r"^[0-9a-f]{12}$")


def normalize_mac(raw) -> str | None:
    if not isinstance(raw, str) or len(raw.strip()) > 32:
        return None
    hexa = re.sub(r"[:.\-]", "", raw.strip()).lower()
    if not _HEX.fullmatch(hexa) or hexa in ("000000000000", "ffffffffffff") or int(hexa[:2], 16) & 1:
        return None
    return ":".join(hexa[i:i + 2] for i in range(0, 12, 2))


def randomized(mac: str) -> bool:
    try:
        return bool(int(mac[:2], 16) & 2)
    except ValueError:
        return False


def _host(value) -> str | None:
    if not isinstance(value, str):
        return None
    name = value.strip().rstrip(".").lower()
    name = name[:-6] if name.endswith(".local") else name
    return name if name and len(name) <= 253 else None


def _mac_of(known: dict) -> str | None:
    return normalize_mac(known.get("mac"))


def _by_host(known: list[dict], name: str, skip: str) -> dict | None:
    for k in known:
        mac = _mac_of(k)
        if k.get("key") != skip and _host(k.get("hostname")) == name and (mac is None or randomized(mac)):
            return k
    return None


def _orphans(known: list[dict], ip: str | None, keep: str) -> list[str]:
    if not ip:
        return []
    return [k["key"] for k in known if k.get("key") != keep and str(k.get("key", "")).startswith("ip:")
            and k.get("ip") == ip and _mac_of(k) is None]


def resolve(known: list[dict], seen: dict) -> dict | None:
    raw_ip = seen.get("ip")
    ip = raw_ip.strip() if isinstance(raw_ip, str) and raw_ip.strip() and len(raw_ip.strip()) <= 45 else None
    name = _host(seen.get("hostname"))
    if seen.get("own"):
        return {"key": SELF_KEY, "mac": None, "randomized": False, "merge": _orphans(known, ip, SELF_KEY)}
    mac = normalize_mac(seen.get("mac"))
    if mac:
        random = randomized(mac)
        exact = any(k.get("key") == mac for k in known)
        key = mac
        if not exact and random and name:
            found = _by_host(known, name, mac)
            key = found["key"] if found else mac
        return {"key": key, "mac": mac, "randomized": random, "merge": _orphans(known, ip, key)}
    if not ip:
        return None
    found = _by_host(known, name, "") if name else None
    if found:
        return {"key": found["key"], "mac": None, "randomized": False, "merge": []}
    for k in known:
        kmac = _mac_of(k)
        if k.get("ip") == ip and (str(k.get("key", "")).startswith("ip:") or (kmac and not randomized(kmac))):
            return {"key": k["key"], "mac": None, "randomized": False, "merge": []}
    return {"key": f"ip:{ip}", "mac": None, "randomized": False, "merge": []}
