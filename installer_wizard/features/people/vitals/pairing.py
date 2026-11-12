import secrets
import threading
import time

TTL = 600.0


class Pairing:
    def __init__(self) -> None:
        self._codes: dict[str, tuple[str, float]] = {}
        self._lock = threading.Lock()

    def create(self, slug: str, now: float | None = None) -> dict:
        now = now or time.time()
        with self._lock:
            self._codes = {c: v for c, v in self._codes.items() if v[1] > now and v[0] != slug}
            code = f"{secrets.randbelow(1_000_000):06d}"
            self._codes[code] = (slug, now + TTL)
        return {"code": code, "expires_in": int(TTL)}

    def redeem(self, code: str, now: float | None = None) -> str:
        now = now or time.time()
        with self._lock:
            slug, expires = self._codes.pop(str(code), ("", 0.0))
        return slug if expires > now else ""


pairing = Pairing()
