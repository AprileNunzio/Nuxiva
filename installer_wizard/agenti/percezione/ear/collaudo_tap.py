import json
import os
import socket
import time

SOCKET_PATH = os.environ.get("NUXIVA_COLLAUDO_SOCKET", "/var/lib/nuxiva/collaudo/intake.sock")
LEVEL_EVERY = 0.25
NUMERIC_LIMIT = 8
TOKEN_FIELDS = ("lang", "reason", "mode", "source", "state")
_sock: socket.socket | None = None
_last_level = 0.0


def _send(raw: dict) -> None:
    global _sock
    try:
        if _sock is None:
            _sock = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
            _sock.setblocking(False)
        _sock.sendto(json.dumps(raw, separators=(",", ":")).encode(), SOCKET_PATH)
    except OSError:
        _sock = None


def _programme(origin) -> bool:
    try:
        return bool(origin._programme())
    except (AttributeError, TypeError, ValueError):
        return False


def observe(origin, event: dict) -> None:
    global _last_level
    kind = str(event.get("type", "")).lower()
    if not kind or not kind.replace("_", "").isalnum():
        return
    now = time.time()
    if kind == "level":
        if now - _last_level < LEVEL_EVERY:
            return
        _last_level = now
    fields: dict = {"programme": _programme(origin)}
    for key, value in event.items():
        if len(fields) >= NUMERIC_LIMIT + len(TOKEN_FIELDS):
            break
        if key == "speaker" and isinstance(value, str):
            fields["spk_ref"] = value
        elif isinstance(value, (bool, int, float)) and key != "type":
            fields[str(key)] = value
        elif key in TOKEN_FIELDS and isinstance(value, str) and len(value) <= 32:
            fields[key] = value
    _send({"domain": "ear", "level": "trace" if kind == "level" else "info", "kind": kind[:64], "src": "ear",
           "fields": fields, "at_ms": int(now * 1000)})
