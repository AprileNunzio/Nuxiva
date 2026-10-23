import threading
import time

LEASE_TTL = 20.0
SWITCH_MARGIN = 6.0
FACE_BONUS = 12.0
MIN_RSSI, MAX_RSSI = -127.0, 0.0


class Arbiter:
    def __init__(self) -> None:
        self._claims: dict[str, dict] = {}
        self._lock = threading.Lock()

    def claim(self, slug: str, node: str, rssi, face: bool = False, now: float | None = None) -> str:
        now = now or time.time()
        try:
            level = max(MIN_RSSI, min(MAX_RSSI, float(rssi)))
        except (TypeError, ValueError):
            level = MIN_RSSI
        score = level + (FACE_BONUS if face else 0.0)
        with self._lock:
            held = self._claims.get(slug)
            expired = held is None or now - held["at"] > LEASE_TTL
            if expired or held["node"] == node or score > held["score"] + SWITCH_MARGIN:
                self._claims[slug] = {"node": node, "score": score, "at": now, "since": held["since"] if held and not expired and held["node"] == node else now}
                return node
            return held["node"]

    def holder(self, slug: str, now: float | None = None) -> str:
        now = now or time.time()
        with self._lock:
            held = self._claims.get(slug)
            return held["node"] if held and now - held["at"] <= LEASE_TTL else ""

    def view(self, slug: str, now: float | None = None) -> dict | None:
        now = now or time.time()
        with self._lock:
            held = self._claims.get(slug)
            if not held or now - held["at"] > LEASE_TTL:
                return None
            return {"node": held["node"], "score": round(held["score"], 1), "age": round(now - held["at"], 1)}

    def release(self, slug: str, node: str) -> None:
        with self._lock:
            if (self._claims.get(slug) or {}).get("node") == node:
                del self._claims[slug]


arbiter = Arbiter()
