import ipaddress
import re
from urllib.parse import urlsplit

DEFAULT_PORT = 8123
MAX_ADDRESSES = 6
MAX_LENGTH = 200
SPLIT = re.compile(r"[\s,;]+")
HOST = re.compile(r"^[A-Za-z0-9]([A-Za-z0-9.-]{0,251}[A-Za-z0-9])?$")


def normalize(raw: str) -> str:
    text = raw.strip()
    if not text or len(text) > MAX_LENGTH:
        raise ValueError("Indirizzo vuoto o troppo lungo")
    if "://" not in text:
        text = "http://" + text
    parts = urlsplit(text)
    if parts.scheme not in ("http", "https"):
        raise ValueError("Usa un indirizzo che inizia con http:// o https://")
    if parts.username or parts.password or parts.query or parts.fragment:
        raise ValueError("L'indirizzo non deve contenere utente, password o parametri")
    host = parts.hostname or ""
    try:
        port = parts.port
    except ValueError:
        raise ValueError("Porta non valida")
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        ip = None
        if not HOST.match(host):
            raise ValueError("Nome o indirizzo IP non valido")
    if ip is not None and (ip.is_link_local or ip.is_multicast or ip.is_unspecified):
        raise ValueError("Indirizzo non consentito")
    if port is None and parts.scheme == "http" and "://" not in raw.strip():
        port = DEFAULT_PORT
    shown = f"[{host}]" if ip is not None and ip.version == 6 else host
    path = parts.path.rstrip("/")
    return f"{parts.scheme}://{shown}{f':{port}' if port else ''}{path}"


def parse(value: str | list) -> list[str]:
    items = value if isinstance(value, list) else SPLIT.split(str(value))
    found: list[str] = []
    for item in items:
        if not str(item).strip():
            continue
        address = normalize(str(item))
        if address not in found:
            found.append(address)
    if len(found) > MAX_ADDRESSES:
        raise ValueError(f"Al massimo {MAX_ADDRESSES} indirizzi")
    return found


def lenient(value: str) -> list[str]:
    out: list[str] = []
    for item in SPLIT.split(value or ""):
        try:
            address = normalize(item) if item.strip() else ""
        except ValueError:
            continue
        if address and address not in out:
            out.append(address)
    return out[:MAX_ADDRESSES]


def candidates(primary: str, extra: str) -> list[str]:
    return lenient(" ".join(x for x in (primary, extra) if x))
