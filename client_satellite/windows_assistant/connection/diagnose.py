import errno
import ipaddress
import socket
import ssl
from urllib.parse import urlsplit

from i18n.strings import t

TIMEOUT_CODES = {10060, errno.ETIMEDOUT}
REFUSED_CODES = {10061, errno.ECONNREFUSED}
UNREACHABLE_CODES = {10051, 10065, errno.ENETUNREACH, errno.EHOSTUNREACH}
PROBE_PORTS = (443, 8443)
PROBE_TIMEOUT = 3.0


def kind_of(exc: BaseException) -> str:
    if isinstance(exc, socket.gaierror):
        return "dns"
    if isinstance(exc, ssl.SSLError):
        return "tls"
    if isinstance(exc, (TimeoutError, socket.timeout)):
        return "timeout"
    code = getattr(exc, "winerror", None) or getattr(exc, "errno", None)
    if code in TIMEOUT_CODES:
        return "timeout"
    if code in REFUSED_CODES:
        return "refused"
    if code in UNREACHABLE_CODES:
        return "unreachable"
    return "other"


def _scope(host: str) -> str:
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        return "name"
    if address.is_loopback:
        return "loopback"
    return "private" if address.is_private else "public"


def explain(exc: BaseException, host: str, port: int) -> str:
    scope = _scope(host)
    if scope == "loopback":
        return t("net.loopback", host=host, port=port)
    return t(f"net.{kind_of(exc)}", host=host, port=port, detail=str(exc))


def _tcp(host: str, port: int, timeout: float) -> str:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return "open"
    except OSError as exc:
        return kind_of(exc)


def probe(server: str, timeout: float = PROBE_TIMEOUT) -> list[str]:
    parts = urlsplit(server)
    host, port = parts.hostname or "", parts.port or 443
    if not host:
        return [t("net.no_address")]
    lines = [t("net.probe.target", host=host, port=port)]
    try:
        addresses = sorted({item[4][0] for item in socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)})
    except socket.gaierror as exc:
        return [*lines, t("net.probe.dns_failed", host=host, detail=str(exc))]
    lines.append(t("net.probe.resolved", addresses=", ".join(addresses[:4])))
    for candidate in dict.fromkeys((port, *PROBE_PORTS)):
        lines.append(t(f"net.probe.port_{_tcp(host, candidate, timeout)}", port=candidate))
    return lines


def report(server: str, exc: BaseException) -> str:
    parts = urlsplit(server)
    head = explain(exc, parts.hostname or "?", parts.port or 443)
    return "\n".join([head, "", *probe(server)])
