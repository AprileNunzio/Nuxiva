import ipaddress
import json
import socket
from collections.abc import Awaitable, Callable, Iterable
from urllib.parse import urlsplit

import native_core

UNSAFE = frozenset({"POST", "PUT", "PATCH", "DELETE"})
LOOPBACK_NAMES = frozenset({"localhost", "nuxiva.local", "nuxiva"})

Scope = dict
Receive = Callable[[], Awaitable[dict]]
Send = Callable[[dict], Awaitable[None]]


def _header(scope: Scope, name: bytes) -> str:
    for key, value in scope.get("headers") or ():
        if key == name:
            return value.decode("latin-1")
    return ""


def _hostname(authority: str) -> str:
    if not authority:
        return ""
    return (urlsplit(f"//{authority}").hostname or "").lower()


def _origin_hostname(origin: str) -> str:
    if not origin or origin == "null":
        return ""
    return (urlsplit(origin).hostname or "").lower()


def _is_ip(name: str) -> bool:
    try:
        ipaddress.ip_address(name)
    except ValueError:
        return False
    return True


def _machine_names() -> frozenset[str]:
    host = socket.gethostname().strip().lower()
    return frozenset({host, f"{host}.local"} if host else ())


class OriginGuard:

    def __init__(self, app, extra_hosts: Iterable[str] = ()) -> None:
        self.app = app
        self.trusted = LOOPBACK_NAMES | _machine_names() | {h.lower() for h in extra_hosts if h}
        self._engines: tuple = (None, None)

    def _native(self):
        cls = native_core.symbol("RustOriginGuard")
        if cls is None:
            native_core.python_fallback("origin")
            return None
        if self._engines[0] is not cls:
            self._engines = (cls, cls(sorted(self.trusted)))
        return self._engines[1]

    def host_allowed(self, host: str) -> bool:
        native = self._native()
        if native is not None:
            return native.host_allowed(host)
        return bool(host) and (host in self.trusted or _is_ip(host) or host.endswith(".local"))

    def verdict(self, scope: Scope) -> str:
        if scope.get("type") != "http":
            return ""
        native = self._native()
        if native is not None:
            return native.verdict(_header(scope, b"host"), str(scope.get("method") or "GET"),
                                  _header(scope, b"sec-fetch-site"), _header(scope, b"origin"))
        return self._py_verdict(scope)

    def _py_verdict(self, scope: Scope) -> str:
        try:
            host = _hostname(_header(scope, b"host"))
        except ValueError:
            return "untrusted_host"
        if host and not self.host_allowed(host):
            return "untrusted_host"
        if scope.get("method", "GET").upper() not in UNSAFE:
            return ""
        fetch_site = _header(scope, b"sec-fetch-site").lower()
        if fetch_site == "cross-site":
            return "cross_site"
        origin = _header(scope, b"origin")
        try:
            foreign = bool(origin) and _origin_hostname(origin) != host
        except ValueError:
            foreign = True
        if foreign:
            return "foreign_origin"
        return ""

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        reason = self.verdict(scope)
        if not reason:
            await self.app(scope, receive, send)
            return
        body = json.dumps({"detail": "Richiesta rifiutata per sicurezza", "code": f"security.{reason}"}).encode()
        await send({"type": "http.response.start", "status": 403,
                    "headers": [(b"content-type", b"application/json"), (b"content-length", str(len(body)).encode())]})
        await send({"type": "http.response.body", "body": body})
