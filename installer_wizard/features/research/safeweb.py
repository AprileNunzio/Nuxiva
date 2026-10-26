import asyncio
import ipaddress
import socket
from dataclasses import dataclass
from urllib.parse import urljoin, urlsplit

import httpx

MAX_BYTES = 1_500_000
MAX_HOPS = 4
PORTS = {None, 80, 443}
REDIRECTS = {301, 302, 303, 307, 308}
TEXT_TYPES = ("text/html", "application/xhtml", "text/plain", "text/xml", "application/xml", "application/rss+xml", "application/atom+xml", "application/json")
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; Nuxiva-Research/1.0)", "Accept-Language": "it,en;q=0.7"}


class WebError(RuntimeError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


@dataclass(frozen=True, slots=True)
class Page:
    url: str
    status: int
    content_type: str
    text: str
    modified: str


def _global(address: str) -> bool:
    try:
        return ipaddress.ip_address(address.split("%")[0]).is_global
    except ValueError:
        return False


def _resolve(host: str) -> list[str]:
    try:
        return [info[4][0] for info in socket.getaddrinfo(host, None, type=socket.SOCK_STREAM)]
    except OSError:
        raise WebError("unreachable")


async def check(url: str) -> None:
    parts = urlsplit(url)
    if parts.scheme not in ("http", "https") or not parts.hostname or parts.username or parts.password:
        raise WebError("blocked_url")
    try:
        port = parts.port
    except ValueError:
        raise WebError("blocked_url")
    if port not in PORTS:
        raise WebError("blocked_url")
    host = parts.hostname
    addresses = [host] if _literal(host) else await asyncio.to_thread(_resolve, host)
    if not addresses or not all(_global(address) for address in addresses):
        raise WebError("blocked_url")


def _literal(host: str) -> bool:
    try:
        ipaddress.ip_address(host)
    except ValueError:
        return False
    return True


async def _read(response: httpx.Response, limit: int) -> bytes:
    chunks: list[bytes] = []
    size = 0
    async for chunk in response.aiter_bytes():
        chunks.append(chunk)
        size += len(chunk)
        if size >= limit:
            break
    return b"".join(chunks)[:limit]


async def fetch(url: str, max_bytes: int = MAX_BYTES, timeout: float = 10.0) -> Page:
    current = url
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=False, headers=HEADERS) as client:
        for _ in range(MAX_HOPS + 1):
            await check(current)
            try:
                async with client.stream("GET", current) as response:
                    if response.status_code in REDIRECTS and response.headers.get("location"):
                        current = urljoin(current, response.headers["location"])
                        continue
                    kind = response.headers.get("content-type", "").split(";")[0].strip().lower()
                    if response.status_code >= 400:
                        raise WebError("unreachable")
                    if not kind.startswith(TEXT_TYPES):
                        raise WebError("bad_type")
                    body = await _read(response, max_bytes)
                    return Page(str(response.url), response.status_code, kind, body.decode(response.encoding or "utf-8", errors="replace"),
                                response.headers.get("last-modified", ""))
            except httpx.HTTPError:
                raise WebError("unreachable")
    raise WebError("too_many_redirects")
