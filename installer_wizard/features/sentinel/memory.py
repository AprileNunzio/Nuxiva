import json
import logging
import secrets
import threading
import time
from datetime import date, datetime, timedelta

import native_module
from features.sentinel import memory_vault as store
from features.sentinel import vault
from features.sentinel.journal import SentinelUnavailable, day_of

log = logging.getLogger("nuxiva.sentinel.memory")
SWEEP_SECONDS = 6 * 3600.0
PROFILE_DAYS = 90
MAX_SPAN_DAYS = 31


def _engine_class():
    return native_module.feature("RustMemory")


def new_id() -> str:
    return secrets.token_hex(16)


class Memory:

    def __init__(self, clock=time.time) -> None:
        self.clock = clock
        self._lock = threading.RLock()
        self.engine = None
        self.heads: dict[str, str | None] = {}
        self.swept_at = 0.0

    def ready(self):
        with self._lock:
            if self.engine is None:
                engine = _engine_class()
                if engine is None:
                    raise SentinelUnavailable("sentinel.memory.native.missing")
                stored = store.load_policy()
                self.engine = engine(vault.secret("memory"), json.dumps(stored) if stored else None)
            return self.engine

    def configure(self, policy: dict | None) -> dict:
        with self._lock:
            engine = _engine_class()
            if engine is None:
                raise SentinelUnavailable("sentinel.memory.native.missing")
            candidate = engine(vault.secret("memory"), json.dumps(policy) if policy else None)
            store.save_policy(policy or {})
            self.engine = candidate
            return json.loads(candidate.policy())

    def policy(self) -> dict:
        return json.loads(self.ready().policy())

    def _key(self, day: str) -> bytes:
        return store.wrapped_key(day, self.ready().new_day_key)

    def _head(self, day: str) -> str | None:
        if day in self.heads:
            return self.heads[day]
        data = store.read_day(day)
        if not data:
            self.heads[day] = None
            return None
        head, _, valid, torn = self.ready().verify(day, data)
        if torn:
            log.error("Memoria di Sentinella del %s con una scrittura interrotta: coda messa da parte", day)
            store.set_aside(day, valid)
        self.heads[day] = head
        return head

    def add(self, sighting: dict) -> str:
        with self._lock:
            day = day_of(sighting["start_ms"] / 1000)
            wrapped = self._key(day)
            frame, head = self.ready().seal(wrapped, day, self._head(day), json.dumps(sighting))
            store.append_day(day, bytes(frame))
            self.heads[day] = head
        self._maybe_sweep()
        return sighting["id"]

    def _days(self, from_ms: int, to_ms: int, limit: int = MAX_SPAN_DAYS) -> list[str]:
        first = datetime.fromtimestamp(from_ms / 1000).date()
        last = datetime.fromtimestamp(to_ms / 1000).date()
        span = (last - first).days
        if span < 0 or span > limit:
            raise ValueError("sentinel.memory.span")
        wanted = {(first + timedelta(days=n)).isoformat() for n in range(span + 1)}
        return [d for d in store.days() if d in wanted]

    def _bundle(self, days: list[str]) -> list[tuple[bytes, str, bytes]]:
        return [(self._key(d), d, store.read_day(d)) for d in days]

    def search(self, query: dict) -> dict:
        with self._lock:
            days = self._bundle(self._days(int(query["from_ms"]), int(query["to_ms"])))
            return json.loads(self.ready().search(json.dumps(query), days))

    def profile(self, who: dict, days_back: int = PROFILE_DAYS) -> dict:
        now = int(self.clock() * 1000)
        with self._lock:
            days = self._bundle(self._days(now - days_back * 86_400_000, now, days_back))
            return json.loads(self.ready().profile(json.dumps(who), days))

    def _rewrite_all(self, apply) -> int:
        changed = 0
        with self._lock:
            for day in store.days():
                data = store.read_day(day)
                if not data:
                    continue
                result = apply(self._key(day), day, data)
                if result is None:
                    continue
                new_data, head, count, moved = result
                store.replace_day(day, bytes(new_data))
                self.heads[day] = head if count else None
                changed += moved
        return changed

    def forget(self, who: dict) -> int:
        raw = json.dumps(who)
        return self._rewrite_all(lambda key, day, data: self.ready().erase(key, day, data, raw))

    def relink(self, source: dict, target: dict) -> int:
        a, b = json.dumps(source), json.dumps(target)
        return self._rewrite_all(lambda key, day, data: self.ready().relink(key, day, data, a, b))

    def pin(self, day: str, ident: str, pinned: bool) -> bool:
        with self._lock:
            data = store.read_day(day)
            result = self.ready().pin(self._key(day), day, data, ident, pinned) if data else None
            if result is None:
                return False
            new_data, head, _, _ = result
            store.replace_day(day, bytes(new_data))
            self.heads[day] = head
            return True

    def _maybe_sweep(self) -> None:
        now = self.clock()
        if now - self.swept_at < SWEEP_SECONDS:
            return
        self.swept_at = now
        threading.Thread(target=self._sweep_logged, name="sentinel-memory-sweep", daemon=True).start()

    def _sweep_logged(self) -> None:
        try:
            self.sweep()
        except (OSError, ValueError, SentinelUnavailable) as exc:
            log.error("Pulizia della memoria di Sentinella non riuscita: %s", exc)

    def sweep(self) -> dict:
        today = date.fromtimestamp(self.clock())
        destroyed, trimmed = [], 0
        with self._lock:
            engine = self.ready()
            for day in store.days():
                age = max(0, min(65535, (today - date.fromisoformat(day)).days))
                if engine.day_expired(age):
                    store.destroy(day)
                    self.heads.pop(day, None)
                    destroyed.append(day)
                    continue
                data = store.read_day(day)
                result = engine.compact(self._key(day), day, data, age) if data else None
                if result is None:
                    continue
                new_data, head, count, removed = result
                store.replace_day(day, bytes(new_data))
                self.heads[day] = head if count else None
                trimmed += removed
        if destroyed or trimmed:
            log.info("Memoria di Sentinella: %d giorni cancellati, %d passaggi scaduti rimossi", len(destroyed), trimmed)
        return {"destroyed": destroyed, "trimmed": trimmed}


memory = Memory()
