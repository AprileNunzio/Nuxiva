import os
import threading
import time

CACHE = 30.0
RESTRICTED_ROLES = frozenset({"guest", "service"})


def _native():
    if os.environ.get("NUXIVA_NATIVE", "auto").strip() == "0":
        return None
    try:
        import nuxiva_native
    except ImportError:
        return None
    return getattr(nuxiva_native, "vitals_camera_allowed", None)


_NATIVE = _native()


def _flag(value) -> bool | None:
    return value if isinstance(value, bool) else None


def py_decide(consent: bool | None, camera_vitals: bool | None, role: str, share_health: bool | None) -> bool:
    if consent is False or camera_vitals is False:
        return False
    if role in RESTRICTED_ROLES:
        return share_health is True
    return True


def decide(profile: dict | None) -> bool:
    if not isinstance(profile, dict):
        return False
    role = profile.get("role") if isinstance(profile.get("role"), str) else ""
    args = (_flag(profile.get("consent")), _flag(profile.get("camera_vitals")), role[:32], _flag(profile.get("share_health")))
    return bool(_NATIVE(*args)) if _NATIVE is not None else py_decide(*args)


class Consent:

    def __init__(self) -> None:
        self._cache: dict[str, tuple[bool, float]] = {}
        self._lock = threading.Lock()

    def allowed(self, slug: str, now: float | None = None) -> bool:
        now = now or time.time()
        with self._lock:
            cached = self._cache.get(slug)
        if cached and now - cached[1] < CACHE:
            return cached[0]
        from agenti.people import people
        verdict = decide(people.load(slug))
        with self._lock:
            self._cache[slug] = (verdict, now)
        return verdict

    def forget(self, slug: str | None = None) -> None:
        with self._lock:
            if slug is None:
                self._cache.clear()
            else:
                self._cache.pop(slug, None)


consent = Consent()
