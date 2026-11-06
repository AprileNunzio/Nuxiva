import base64
import hashlib
import hmac
import logging
import os
import secrets
import time

import native_module
from config import ETC_DIR

SESSION_COOKIE = "nuxiva_session"
DISPLAY_COOKIE = "nuxiva_display"
SESSION_TTL = 12 * 3600
ADMIN_GROUPS = {"sudo", "wheel", "nuxiva-admin"}
_SECRET_FILE = ETC_DIR / "session.key"
log = logging.getLogger("nuxiva.auth")
_failures: dict = {}
_engines: dict = {"codec": None, "codec_key": None, "limiter": None, "limiter_key": None}


def _secret() -> bytes:
    try:
        fd = os.open(_SECRET_FILE, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        return _SECRET_FILE.read_bytes()
    with os.fdopen(fd, "wb") as handle:
        handle.write(secrets.token_bytes(32))
    return _SECRET_FILE.read_bytes()


def _is_admin_user(username: str) -> bool:
    if os.environ.get("NUXIVA_TEST_AUTH") == "1" and username in ("admin", "user"):
        return True
    if username == "root":
        return True
    import grp
    import pwd
    try:
        primary = grp.getgrgid(pwd.getpwnam(username).pw_gid).gr_name
    except KeyError:
        return False
    groups = {g.gr_name for g in grp.getgrall() if username in g.gr_mem} | {primary}
    return bool(groups & ADMIN_GROUPS)


def _native(kind: str, name: str, *args):
    cls = native_module.feature(name)
    if cls is None:
        native_module.python_fallback("auth")
        return None
    key = (cls, hashlib.sha256(b"".join(args)).digest())
    if _engines[f"{kind}_key"] != key:
        _engines[kind] = cls(*args)
        _engines[f"{kind}_key"] = key
    return _engines[kind]


def _limiter():
    return _native("limiter", "RustLoginLimiter")


def _codec():
    return _native("codec", "RustSessionCodec", _secret())


def rate_limited(ip: str) -> bool:
    limiter = _limiter()
    if limiter is not None:
        return limiter.limited(ip, time.time())
    return _py_rate_limited(ip)


def _record_failure(ip: str) -> None:
    limiter = _limiter()
    if limiter is not None:
        limiter.fail(ip, time.time())
        return
    _failures.setdefault(ip, []).append(time.time())


def _py_rate_limited(ip: str) -> bool:
    now = time.time()
    attempts = [t for t in _failures.get(ip, []) if now - t < 300]
    _failures[ip] = attempts
    return len(attempts) >= 5


def authenticate(username: str, password: str, ip: str) -> bool:
    if rate_limited(ip):
        return False
    ok = False
    if username and password:
        if os.environ.get("NUXIVA_TEST_AUTH") == "1":
            ok = username == "admin" and password == "nuxiva"
        else:
            try:
                import pam
                ok = pam.pam().authenticate(username, password, service="nuxiva-admin") and _is_admin_user(username)
            except Exception:
                log.exception("Autenticazione PAM non riuscita per errore interno")
                ok = False
    if not ok:
        _record_failure(ip)
    return ok


def issue(username: str) -> str:
    codec = _codec()
    if codec is not None:
        return codec.issue(username, int(time.time()), SESSION_TTL)
    return _py_issue(username)


def verify(token: str | None) -> str | None:
    if not token:
        return None
    codec = _codec()
    if codec is not None:
        return codec.verify(token, time.time())
    return _py_verify(token)


def _py_issue(username: str) -> str:
    payload = f"{username}|{int(time.time()) + SESSION_TTL}"
    sig = hmac.new(_secret(), payload.encode(), hashlib.sha256).hexdigest()
    return base64.urlsafe_b64encode(f"{payload}|{sig}".encode()).decode()


def _py_verify(token: str | None) -> str | None:
    if not token:
        return None
    try:
        username, expires, sig = base64.urlsafe_b64decode(token.encode()).decode().rsplit("|", 2)
    except (ValueError, UnicodeDecodeError):
        return None
    if not expires.isdigit():
        return None
    expected = hmac.new(_secret(), f"{username}|{expires}".encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(sig, expected) or int(expires) < time.time():
        return None
    return username
