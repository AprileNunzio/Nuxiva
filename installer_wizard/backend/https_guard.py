import ipaddress
import re
from collections.abc import Awaitable, Callable
from urllib.parse import quote

from config import env_get

Scope = dict
Receive = Callable[[], Awaitable[dict]]
Send = Callable[[dict], Awaitable[None]]

LOOPBACK = frozenset({"127.0.0.1", "::1", "localhost"})
EXEMPT = ("/nuxiva-ca.crt", "/api/secure/status", "/healthz", "/api/health")
AUTHORITY_RE = re.compile(r"^(?:\[(?P<v6>[0-9a-f:.]{2,45})\]|(?P<name>[a-z0-9.-]{1,253}))(?::[0-9]{1,5})?$")
HSTS = b"max-age=31536000"
DEVICES = b"camera=(self), microphone=(self), geolocation=(self), display-capture=(self), fullscreen=(self)"
SECURITY_HEADERS = (
    (b"permissions-policy", DEVICES),
    (b"x-content-type-options", b"nosniff"),
    (b"referrer-policy", b"same-origin"),
)


def enforced() -> bool:
    return env_get("NUXIVA_FORCE_HTTPS", "1").strip().lower() not in ("0", "off", "no", "false")


def tls_port() -> int:
    from features.secure.api import active_port
    return active_port()


def _header(scope: Scope, name: bytes) -> str:
    for key, value in scope.get("headers") or ():
        if key == name:
            return value.decode("latin-1")
    return ""


def _safe_host(authority: str) -> str:
    match = AUTHORITY_RE.match(authority.strip().lower())
    if not match:
        return ""
    host = match.group("v6") or match.group("name")
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        return host if match.group("name") and ".." not in host and not host.startswith((".", "-")) else ""
    return f"[{address.compressed}]" if address.version == 6 else address.compressed


def _navigation(scope: Scope) -> bool:
    if scope.get("method", "GET").upper() not in ("GET", "HEAD"):
        return False
    mode = _header(scope, b"sec-fetch-mode").lower()
    if mode:
        return mode == "navigate"
    return "text/html" in _header(scope, b"accept").lower()


def redirect_target(scope: Scope, admin: bool, port: int) -> str:
    if scope.get("type") != "http" or scope.get("scheme") != "http" or port <= 0:
        return ""
    client = scope.get("client") or ("", 0)
    if client[0] in LOOPBACK:
        return ""
    path = scope.get("path") or "/"
    if path.startswith(EXEMPT) or not _navigation(scope):
        return ""
    host = _safe_host(_header(scope, b"host"))
    if not host:
        return ""
    authority = host if port == 443 else f"{host}:{port}"
    prefix = "/admin" if admin else ""
    query = scope.get("query_string", b"").decode("latin-1")
    target = f"https://{authority}{prefix}{quote(path, safe='/-._~')}"
    return f"{target}?{quote(query, safe='=&-._~%+')}" if query else target


class HttpsGuard:

    def __init__(self, app, admin: bool = False) -> None:
        self.app = app
        self.admin = admin

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope.get("type") != "http":
            await self.app(scope, receive, send)
            return
        target = redirect_target(scope, self.admin, tls_port()) if enforced() else ""
        if target:
            await send({"type": "http.response.start", "status": 308,
                        "headers": [(b"location", target.encode("latin-1")), (b"content-length", b"0"),
                                    (b"cache-control", b"no-store"), *SECURITY_HEADERS]})
            await send({"type": "http.response.body", "body": b""})
            return
        secure = scope.get("scheme") == "https"

        async def decorate(message: dict) -> None:
            if message.get("type") == "http.response.start":
                headers = list(message.get("headers") or [])
                present = {key.lower() for key, _ in headers}
                extra = [*SECURITY_HEADERS, *([(b"strict-transport-security", HSTS)] if secure else [])]
                headers.extend((key, value) for key, value in extra if key not in present)
                message = {**message, "headers": headers}
            await send(message)

        await self.app(scope, receive, decorate)
