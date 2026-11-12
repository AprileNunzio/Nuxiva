import hashlib
import secrets
import time
from dataclasses import dataclass, replace

from fastapi import HTTPException, Request

import auth
from access import session_user
from config import env_get
from agenti.nodes.display_link import COOKIE, display_node

TTL_SECONDS = 15
MAX_SESSIONS = 64
MAX_PER_LOGIN = 4
SESSION_HEADER = "x-nuxiva-camera-session"


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


@dataclass(frozen=True)
class Lease:
    owner: str
    expires_at: float
    next_frame_at: float = 0.0


class CameraSessions:
    def __init__(self, clock=time.monotonic) -> None:
        self._clock = clock
        self._leases: dict[str, Lease] = {}

    def _prune(self, now: float) -> None:
        self._leases = {key: lease for key, lease in self._leases.items() if lease.expires_at > now}

    def issue(self, owner: str) -> str:
        now = self._clock()
        self._prune(now)
        if len(self._leases) >= MAX_SESSIONS or sum(lease.owner == owner for lease in self._leases.values()) >= MAX_PER_LOGIN:
            raise HTTPException(429, "camera.session.limit")
        token = secrets.token_urlsafe(32)
        self._leases[_digest(token)] = Lease(owner, now + TTL_SECONDS)
        return token

    def _lookup(self, token: str, owner: str) -> tuple[str, Lease] | None:
        if len(token) != 43:
            return None
        now = self._clock()
        self._prune(now)
        key = _digest(token)
        lease = self._leases.get(key)
        if lease is None or lease.owner != owner:
            return None
        return key, lease

    def active(self, token: str, owner: str) -> bool:
        return self._lookup(token, owner) is not None

    def update(self, token: str, owner: str, *, revoke: bool = False) -> bool:
        entry = self._lookup(token, owner)
        if entry is None:
            return False
        key, lease = entry
        if revoke:
            del self._leases[key]
        else:
            self._leases[key] = replace(lease, expires_at=self._clock() + TTL_SECONDS)
        return True

    def admit_frame(self, token: str, owner: str) -> None:
        entry = self._lookup(token, owner)
        if entry is None:
            raise HTTPException(404, "camera.session.expired")
        key, lease = entry
        now = self._clock()
        if now < lease.next_frame_at:
            raise HTTPException(429, "camera.frame.rate")
        self._leases[key] = replace(lease, next_frame_at=now + 1.0)


def camera_owner(request: Request) -> str:
    host = request.headers.get("host")
    if (request.url.scheme != "https" or not host or request.headers.get("origin") != f"https://{host}"
            or request.headers.get("x-nuxiva-request") != "1"):
        raise HTTPException(403, "camera.session.origin")
    if session_user(request):
        return _digest("user:" + request.cookies[auth.SESSION_COOKIE])
    if display_node(request):
        return _digest("node:" + request.cookies[COOKIE])
    raise HTTPException(401, "camera.session.identity")


def require_camera_enabled() -> None:
    if env_get("NUXIVA_REMOTE_CAMERA_PREVIEW", "0") != "1":
        raise HTTPException(403, "camera.session.disabled")


camera_sessions = CameraSessions()
