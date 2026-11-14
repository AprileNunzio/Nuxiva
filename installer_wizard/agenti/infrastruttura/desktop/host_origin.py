import ipaddress
import socket
import threading
import time

import native_core

MAX_LOCAL_ADDRESSES = 512
MAX_HOST_LEN = 255
REFRESH_SECONDS = 15.0

_lock = threading.Lock()
_cache: tuple[float, tuple[str, ...]] = (0.0, ())


def _interface_addresses() -> list[str]:
    found: list[str] = []
    try:
        import psutil
        for entries in psutil.net_if_addrs().values():
            for entry in entries:
                if entry.family in (socket.AF_INET, socket.AF_INET6):
                    found.append(entry.address)
    except (ImportError, OSError):
        pass
    if not found:
        try:
            for info in socket.getaddrinfo(socket.gethostname(), None):
                found.append(str(info[4][0]))
        except OSError:
            pass
    return found


def local_addresses(now: float | None = None) -> tuple[str, ...]:
    global _cache
    moment = time.monotonic() if now is None else now
    stamp, cached = _cache
    if cached and moment - stamp < REFRESH_SECONDS:
        return cached
    with _lock:
        stamp, cached = _cache
        if cached and moment - stamp < REFRESH_SECONDS:
            return cached
        fresh = tuple(_interface_addresses()[:MAX_LOCAL_ADDRESSES])
        _cache = (moment, fresh)
        return fresh


def reset_cache() -> None:
    global _cache
    _cache = (0.0, ())


def _unmapped(ip):
    mapped = getattr(ip, "ipv4_mapped", None)
    return mapped if mapped is not None else ip


def parse_address(raw: str):
    text = str(raw).strip().split("%", 1)[0]
    if not text or len(text) > MAX_HOST_LEN:
        return None
    try:
        return _unmapped(ipaddress.ip_address(text))
    except ValueError:
        return None


def _usable(ip) -> bool:
    return not (ip.is_unspecified or ip.is_multicast)


def _own(ip, locals_: set) -> bool:
    return _usable(ip) and (ip.is_loopback or ip in locals_)


def _host_name(header: str) -> str | None:
    value = header.strip()
    if not value or len(value) > MAX_HOST_LEN or any(ord(c) < 32 or ord(c) == 127 for c in value):
        return None
    if value.startswith("["):
        inside, closed, _ = value[1:].partition("]")
        return inside if closed else None
    try:
        ipaddress.IPv6Address(value)
        return value
    except ValueError:
        return value.rpartition(":")[0] if ":" in value else value


def python_is_host_origin(peer: str, host: str, locals_: list[str]) -> bool:
    own = {ip for ip in (parse_address(item) for item in locals_[:MAX_LOCAL_ADDRESSES]) if ip is not None and _usable(ip)}
    address = parse_address(peer)
    if not (peer.strip().lower() == "localhost" or (address is not None and _own(address, own))):
        return False
    name = _host_name(host)
    if name is None:
        return False
    name = name.rstrip(".")
    if name.lower() == "localhost":
        return True
    target = parse_address(name)
    return target is not None and _own(target, own)


def is_host_origin(peer: str, host: str, locals_: list[str] | tuple[str, ...] | None = None) -> bool:
    addresses = list(local_addresses() if locals_ is None else locals_)
    native = native_core.symbol("access_is_host_origin")
    if native is not None:
        return bool(native(peer, host, addresses))
    native_core.python_fallback("host_origin")
    return python_is_host_origin(peer, host, addresses)
