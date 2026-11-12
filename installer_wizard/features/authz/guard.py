import threading
import time
from collections import deque

from config import env_get
from state import store

from features.authz.matrix_store import store as matrix
from features.authz.policy import Decision
from features.authz.principal import Principal, Strength
from features.authz.risk import Risk

OUTSIDERS = frozenset({"guest", "anonymous"})
PASSIVE = ("info.", "home.state.read", "risk.info")
WINDOW = 60.0
DEFAULT_RATE = 10
TARGET_KEYS = ("slug", "person", "who")


def rate() -> int:
    try:
        return max(1, min(120, int(env_get("NUXIVA_AUTHZ_GUEST_RATE", str(DEFAULT_RATE)))))
    except ValueError:
        return DEFAULT_RATE


class Throttle:

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._hits: dict[str, deque] = {}

    def allow(self, key: str, now: float, limit: int) -> bool:
        with self._lock:
            hits = self._hits.setdefault(key, deque())
            while hits and now - hits[0] >= WINDOW:
                hits.popleft()
            if len(hits) >= limit:
                return False
            hits.append(now)
            return True

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()


throttle = Throttle()


def speaker_role(who: Principal) -> str:
    if who.role == "system":
        return "system"
    if who.subrole == "child":
        return "child"
    if who.known and who.role not in OUTSIDERS:
        return who.role
    if who.known:
        return "guest"
    audience = (getattr(store, "audience", None) or {}).get("kind")
    return "guest" if audience in ("authorized", "mixed") else "anonymous"


def own(who: Principal, args: dict | None) -> bool:
    given = args if isinstance(args, dict) else {}
    target = next((str(given[k]).strip().lower() for k in TARGET_KEYS if given.get(k)), "")
    return not target or (who.known and target == who.slug.lower())


def _active(capabilities: list[str]) -> bool:
    return any(not c.startswith(PASSIVE) for c in capabilities)


def decide(who: Principal, capabilities: list[str], level: Risk, args: dict | None = None, count: bool = True) -> Decision:
    role = speaker_role(who)
    if count and role in OUTSIDERS and _active(capabilities):
        key = f"{role}:{who.slug}:{who.source}"
        if not throttle.allow(key, time.time(), rate()):
            return Decision(False, "rate", level)
    kind, detail = matrix.decide(capabilities, role, who.strength.name.lower(), None, own(who, args))
    if kind == "allow":
        return Decision(True, "ok", level)
    if kind == "confirm":
        return Decision(True, "confirm", level, Strength.SINGLE)
    if kind == "proof":
        return Decision(False, "proof", level, Strength[detail.upper()])
    return Decision(False, detail or "role", level)
