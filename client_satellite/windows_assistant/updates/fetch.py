import errno
import hashlib
import http.client
import random
import socket
import ssl
import threading
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from updates.errors import UpdateCancelled, UpdateFailure

AGENT = "NUXIVA-Assistente"
JSON = "application/vnd.github+json"
BINARY = "application/octet-stream"
TIMEOUT = 30
ATTEMPTS = 4
BASE_DELAY = 2.0
MAX_DELAY = 60.0
CHUNK = 1 << 16
TRANSIENT_STATUS = frozenset({408, 425, 429, 500, 502, 503, 504})
TRUSTED_HOSTS = frozenset({
    "api.github.com", "github.com", "objects.githubusercontent.com", "release-assets.githubusercontent.com",
})


def trusted(url: str) -> bool:
    parts = urllib.parse.urlsplit(url)
    return parts.scheme == "https" and (parts.hostname or "") in TRUSTED_HOSTS and parts.port in (None, 443)


class _TrustedRedirects(urllib.request.HTTPRedirectHandler):
    max_redirections = 5

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if not trusted(newurl):
            raise UpdateFailure("server_rejected", f"redirect {urllib.parse.urlsplit(newurl).hostname}")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


_CONTEXT = ssl.create_default_context()
_CONTEXT.minimum_version = ssl.TLSVersion.TLSv1_2
_OPENER = urllib.request.build_opener(urllib.request.HTTPSHandler(context=_CONTEXT), _TrustedRedirects())


def _classify(exc: BaseException) -> UpdateFailure:
    if isinstance(exc, UpdateFailure):
        return exc
    if isinstance(exc, urllib.error.HTTPError):
        return UpdateFailure("server_rejected", f"HTTP {exc.code}", exc.code in TRANSIENT_STATUS)
    reason = getattr(exc, "reason", exc)
    if isinstance(reason, ssl.SSLCertVerificationError):
        return UpdateFailure("network_unreachable", "TLS certificate")
    if isinstance(reason, (socket.timeout, TimeoutError)):
        return UpdateFailure("network_unreachable", "timeout", True)
    if isinstance(reason, socket.gaierror):
        return UpdateFailure("network_unreachable", "DNS", True)
    return UpdateFailure("network_unreachable", type(reason).__name__, True)


def _open(url: str, accept: str):
    if not trusted(url):
        raise UpdateFailure("server_rejected", f"host {urllib.parse.urlsplit(url).hostname}")
    request = urllib.request.Request(url, headers={"User-Agent": AGENT, "Accept": accept})
    try:
        return _OPENER.open(request, timeout=TIMEOUT)
    except (urllib.error.URLError, http.client.HTTPException, OSError) as exc:
        raise _classify(exc) from exc


def _retrying(action, stop: threading.Event):
    for attempt in range(1, ATTEMPTS + 1):
        try:
            return action()
        except UpdateFailure as failure:
            if not failure.transient or attempt == ATTEMPTS:
                raise
        delay = min(MAX_DELAY, BASE_DELAY * 2 ** (attempt - 1)) * random.uniform(0.5, 1.0)
        if stop.wait(delay):
            raise UpdateCancelled()
    raise UpdateFailure("download_failed", "retries exhausted")


def get(url: str, limit: int, stop: threading.Event, accept: str = BINARY) -> bytes:
    def once() -> bytes:
        with _open(url, accept) as response:
            try:
                data = response.read(limit + 1)
            except (http.client.HTTPException, OSError) as exc:
                raise _classify(exc) from exc
        if len(data) > limit:
            raise UpdateFailure("download_failed", f"response over {limit} bytes")
        return data

    return _retrying(once, stop)


def _stream(response, target: Path, size: int, stop: threading.Event) -> str:
    digest, received = hashlib.sha256(), 0
    try:
        with open(target, "wb") as handle:
            while chunk := response.read(CHUNK):
                if stop.is_set():
                    raise UpdateCancelled()
                received += len(chunk)
                if received > size:
                    raise UpdateFailure("hash_mismatch", f"file over {size} bytes")
                digest.update(chunk)
                handle.write(chunk)
    except (http.client.HTTPException, socket.timeout, ConnectionError, ssl.SSLError) as exc:
        raise _classify(exc) from exc
    except OSError as exc:
        code = "storage_full" if exc.errno == errno.ENOSPC else "storage_failed"
        raise UpdateFailure(code, exc.strerror or type(exc).__name__) from exc
    if received != size:
        raise UpdateFailure("download_failed", f"incomplete {received}/{size}", True)
    return digest.hexdigest()


def download(url: str, target: Path, size: int, stop: threading.Event) -> str:
    def once() -> str:
        with _open(url, BINARY) as response:
            return _stream(response, target, size, stop)

    return _retrying(once, stop)
