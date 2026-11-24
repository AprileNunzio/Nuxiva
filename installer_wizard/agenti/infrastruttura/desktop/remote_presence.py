import hashlib
import threading
import time

import auth
from access import session_user

TTL_SECONDS = 30.0
MAX_LEASES = 64
DISPLAY_ROLES = frozenset({"owner", "family"})
OUTCOMES = frozenset({
    "matched", "no_face", "many_faces", "small_face", "unknown", "ambiguous", "no_gallery",
    "not_authorized", "liveness_needed", "spoof",
})
REVOKING = frozenset({"unknown", "many_faces", "spoof", "not_authorized", "ambiguous"})
NAME_LIMIT = 64


def viewer(request) -> str | None:
    if request.url.scheme != "https" or not session_user(request):
        return None
    return hashlib.sha256(("viewer:" + request.cookies[auth.SESSION_COOKIE]).encode()).hexdigest()


def probe_session(token: str) -> str:
    return hashlib.sha256(("probe:" + token).encode()).hexdigest()


def judge(payload, role: str, liveness_mode: str) -> dict:
    data = payload if isinstance(payload, dict) else {}
    outcome = data.get("outcome")
    if outcome not in OUTCOMES:
        return {"outcome": "unavailable"}
    if outcome != "matched":
        return {"outcome": outcome}
    alive = data.get("liveness")
    if liveness_mode != "off" and alive == "spoof":
        return {"outcome": "spoof"}
    if role not in DISPLAY_ROLES:
        return {"outcome": "not_authorized"}
    if liveness_mode == "strict" and alive != "live":
        return {"outcome": "liveness_needed"}
    return {"outcome": "matched", "slug": str(data.get("slug") or ""), "name": str(data.get("name") or "")[:NAME_LIMIT]}


class RemotePresence:

    def __init__(self, clock=time.monotonic) -> None:
        self._clock = clock
        self._lock = threading.Lock()
        self._leases: dict[str, tuple[str, float]] = {}

    def _prune(self, now: float) -> None:
        self._leases = {key: lease for key, lease in self._leases.items() if lease[1] > now}

    def grant(self, holder: str | None, slug: str) -> bool:
        if not holder or not slug:
            return False
        with self._lock:
            now = self._clock()
            self._prune(now)
            if holder not in self._leases and len(self._leases) >= MAX_LEASES:
                return False
            self._leases[holder] = (slug, now + TTL_SECONDS)
            return True

    def revoke(self, holder: str | None) -> None:
        if holder:
            with self._lock:
                self._leases.pop(holder, None)

    def holder(self, holder: str | None) -> str | None:
        if not holder:
            return None
        with self._lock:
            lease = self._leases.get(holder)
            if lease is None:
                return None
            if lease[1] <= self._clock():
                del self._leases[holder]
                return None
            return lease[0]

    def settle(self, holder: str | None, verdict: dict) -> dict:
        if verdict["outcome"] == "matched":
            if not self.grant(holder, verdict["slug"]):
                return {"outcome": "unavailable"}
            return {"outcome": "matched", "name": verdict["name"]}
        if verdict["outcome"] in REVOKING:
            self.revoke(holder)
        return {"outcome": verdict["outcome"]}


remote_presence = RemotePresence()
