import contextvars
import json
import os
import socket
import threading
import time
import uuid
from contextlib import contextmanager

from agenti.collaudo import paths

_corr: contextvars.ContextVar[str | None] = contextvars.ContextVar("collaudo_corr", default=None)
_local = None
_sock: socket.socket | None = None
_sock_lock = threading.Lock()
MAX_DATAGRAM = 16 * 1024
SRC_FALLBACK = "process"


def bind_local(sink) -> None:
    global _local
    _local = sink


def new_corr() -> str:
    return uuid.uuid4().hex[:16]


@contextmanager
def correlation(value: str | None = None):
    token = _corr.set(value or new_corr())
    try:
        yield _corr.get()
    finally:
        _corr.reset(token)


def current_corr() -> str | None:
    return _corr.get()


def _datagram(payload: bytes) -> bool:
    global _sock
    with _sock_lock:
        try:
            if _sock is None:
                _sock = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
                _sock.setblocking(False)
            _sock.sendto(payload, str(paths.SOCKET))
            return True
        except OSError:
            _sock = None
            return False


def emit(domain: str, level: str, kind: str, src: str | None = None, corr: str | None = None, **fields) -> bool:
    try:
        raw = {"domain": domain, "level": level, "kind": kind, "src": src or os.environ.get("NUXIVA_SERVICE", SRC_FALLBACK),
               "corr": corr or _corr.get(), "fields": fields, "at_ms": int(time.time() * 1000)}
        if _local is not None:
            _local(raw)
            return True
        payload = json.dumps(raw, separators=(",", ":"), default=str).encode()
        return len(payload) <= MAX_DATAGRAM and _datagram(payload)
    except (TypeError, ValueError, OSError, RuntimeError):
        return False
