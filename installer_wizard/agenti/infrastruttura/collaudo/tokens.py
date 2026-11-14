import hashlib
import hmac
import os
import secrets
import time
from collections import deque

import native_core
from agenti.collaudo import paths

PREFIX = "b2:"
LIMIT = 10
WINDOW = 60.0
_failures: deque[float] = deque(maxlen=LIMIT)


def _digest(token: str) -> str:
    return PREFIX + hashlib.blake2b(token.encode(), digest_size=32, key=b"nuxiva.collaudo.token").hexdigest()


def _write(content: str) -> None:
    paths.ROOT.mkdir(parents=True, exist_ok=True, mode=0o700)
    tmp = paths.TOKEN_FILE.with_suffix(".tmp")
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        handle.write(content)
    os.replace(tmp, paths.TOKEN_FILE)


def issue() -> str:
    issuer = native_core.symbol("collaudo_token_issue")
    if issuer is not None:
        paths.ROOT.mkdir(parents=True, exist_ok=True, mode=0o700)
        return issuer(str(paths.TOKEN_FILE))
    token = secrets.token_hex(32)
    _write(_digest(token))
    return token


def revoke() -> None:
    paths.TOKEN_FILE.unlink(missing_ok=True)


def armed() -> bool:
    return paths.TOKEN_FILE.exists()


def verify(token: str) -> bool:
    if len(token) != 64 or not armed():
        return False
    stored = paths.TOKEN_FILE.read_text(encoding="utf-8").strip()
    if stored.startswith(PREFIX):
        return hmac.compare_digest(stored, _digest(token.lower()))
    checker = native_core.symbol("collaudo_token_verify")
    return bool(checker is not None and checker(str(paths.TOKEN_FILE), token))


def throttled() -> bool:
    now = time.monotonic()
    return len(_failures) >= LIMIT and now - _failures[0] < WINDOW


def failed() -> None:
    _failures.append(time.monotonic())
