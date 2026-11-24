import re
import threading
import time
from collections import OrderedDict

MIN_FACE_PX = 36
MAX_SESSIONS = 32
SESSION_TTL = 30.0
SESSION_PATTERN = re.compile(r"^[0-9a-f]{64}$")
NAME_LIMIT = 64


def face_outcome(faces) -> str | None:
    if faces is None or len(faces) == 0:
        return "no_face"
    if len(faces) > 1:
        return "many_faces"
    if min(float(faces[0][2]), float(faces[0][3])) < MIN_FACE_PX:
        return "small_face"
    return None


def identity_outcome(verdict: dict, enrolled: int, liveness: str) -> dict:
    if enrolled <= 0:
        return {"outcome": "no_gallery", "liveness": liveness}
    if verdict.get("ambiguous"):
        return {"outcome": "ambiguous", "liveness": liveness}
    slug = str(verdict.get("slug") or "")
    if not slug:
        return {"outcome": "unknown", "liveness": liveness}
    name = str(verdict.get("name") or "")[:NAME_LIMIT]
    return {"outcome": "matched", "slug": slug, "name": name, "liveness": liveness}


class LivenessBook:

    def __init__(self, factory, clock=time.monotonic) -> None:
        self._factory = factory
        self._clock = clock
        self._lock = threading.Lock()
        self._trackers: OrderedDict[str, tuple[object, float]] = OrderedDict()

    def update(self, session: str, points: list[float], now: float, minimum: float) -> str:
        if not SESSION_PATTERN.fullmatch(session or ""):
            return "unknown"
        with self._lock:
            tick = self._clock()
            for key in [k for k, (_, seen) in self._trackers.items() if tick - seen > SESSION_TTL]:
                del self._trackers[key]
            tracker = self._trackers.pop(session, (None, 0.0))[0] or self._factory()
            self._trackers[session] = (tracker, tick)
            while len(self._trackers) > MAX_SESSIONS:
                self._trackers.popitem(last=False)
        state = tracker.update(points, now, minimum).get("state", "unknown")
        return state if state in ("live", "spoof") else "unknown"

    def __len__(self) -> int:
        return len(self._trackers)
