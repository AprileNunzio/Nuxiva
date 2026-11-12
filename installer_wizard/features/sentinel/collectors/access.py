import threading
import time

from features.sentinel import record

REPEAT_SECONDS = 60.0


class AccessCollector:

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.seen: dict[tuple, float] = {}

    def denied(self, slug: str, role: str, kind: str, name: str, code: str) -> None:
        if not record.enabled():
            return
        now = time.time()
        key = (slug, kind, name, code)
        with self._lock:
            if now - self.seen.get(key, 0.0) < REPEAT_SECONDS:
                return
            self.seen = {k: v for k, v in self.seen.items() if now - v < REPEAT_SECONDS}
            self.seen[key] = now
        if slug:
            from features.sentinel.collectors.presence import display_name
            subject, who = record.person(slug), display_name(slug)
        else:
            subject = record.NUXIVA
            who = "sentinel.word.guest" if role == "guest" else "sentinel.word.someone"
        record.record("access.denied", subject, "sentinel.access.denied",
                      {"who": who, "action": f"{kind} {name}"[:80], "code": code[:32]}, "household", "authz", at=now)


collector = AccessCollector()
