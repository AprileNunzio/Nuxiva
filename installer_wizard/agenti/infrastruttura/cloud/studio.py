import ipaddress
from urllib.parse import urlsplit

FLAVOR = "studio"
DEFAULT_PORT = 8888
LOCKED = {"enable_tools": False}
STRIPPED = ("enabled_tools", "session_id", "tools", "tool_choice")
CGNAT = ipaddress.ip_network("100.64.0.0/10")


def private_host(host: str) -> bool:
    if host.lower() == "localhost":
        return True
    try:
        ip = ipaddress.ip_address(host.strip("[]"))
    except ValueError:
        return False
    return ip.is_loopback or (ip.is_private and not ip.is_link_local) or ip in CGNAT


def studio_addresses(root: str) -> tuple[str, str]:
    parts = urlsplit(root)
    host = parts.hostname or ""
    if parts.username or parts.password or parts.query or parts.fragment or not host:
        raise ValueError("Indirizzo non valido")
    if parts.scheme != "https" and not private_host(host):
        raise ValueError("Fuori dalla rete locale serve https")
    clean = root.rstrip("/").removesuffix("/v1").rstrip("/")
    if parts.port is None and parts.scheme == "http":
        clean += f":{DEFAULT_PORT}"
    return clean, f"{clean}/v1"


def harden(body: dict, entry: dict) -> dict:
    if entry.get("flavor") != FLAVOR:
        return body
    for key in STRIPPED:
        body.pop(key, None)
    body.update(LOCKED)
    return body
