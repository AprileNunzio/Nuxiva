import ipaddress
import re

from config import env_get

DEFAULT_NETWORKS = ("127.", "10.", "172.16.0.0/12", "192.168.")
PREFIX = re.compile(r"^(?:\d{1,3}\.){1,3}$")
PROTOCOLS = ("SMB2_10", "SMB3_00", "SMB3_11")
ENCRYPTION = ("default", "desired", "required")
UPLOAD_LIMITS = (100, 500, 1000, 4000)
DEFAULT_UPLOAD = 1000


def _flag(key: str, default: str) -> bool:
    return env_get(key, default) != "0"


def network(item: str) -> str | None:
    item = item.strip()
    if PREFIX.match(item) and all(int(part) < 256 for part in item.rstrip(".").split(".")):
        return item
    try:
        if "/" in item:
            return str(ipaddress.ip_network(item, strict=False))
        return str(ipaddress.ip_address(item))
    except ValueError:
        return None


def networks(raw: str) -> tuple[str, ...]:
    found = []
    for item in re.split(r"[\s,;]+", str(raw or "")):
        if item:
            clean = network(item)
            if clean is None:
                return DEFAULT_NETWORKS
            found.append(clean)
    return tuple(dict.fromkeys(found)) or DEFAULT_NETWORKS


def choice(value: str, allowed: tuple[str, ...], default: str) -> str:
    return value if value in allowed else default


def upload_limit_mb() -> int:
    try:
        value = int(env_get("NUXIVA_SHARES_UPLOAD_MB", str(DEFAULT_UPLOAD)))
    except ValueError:
        return DEFAULT_UPLOAD
    return value if value in UPLOAD_LIMITS else DEFAULT_UPLOAD


def read() -> dict:
    return {"readonly": env_get("NUXIVA_SHARES_READONLY", "0") == "1",
            "networks": list(networks(env_get("NUXIVA_SHARES_NETWORKS", ""))),
            "recycle": env_get("NUXIVA_SHARES_RECYCLE", "0") == "1",
            "discovery": _flag("NUXIVA_SHARES_DISCOVERY", "1"),
            "upload_mb": upload_limit_mb(),
            "protocol": choice(env_get("NUXIVA_SHARES_PROTOCOL", "SMB2_10"), PROTOCOLS, "SMB2_10"),
            "encrypt": choice(env_get("NUXIVA_SHARES_ENCRYPT", "default"), ENCRYPTION, "default")}
