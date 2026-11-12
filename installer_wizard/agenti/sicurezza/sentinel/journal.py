import json
import logging
import secrets
import threading
import time
from datetime import datetime, timedelta

from agenti.sentinel import vault
import native_module

log = logging.getLogger("nuxiva.sentinel")
DAY_MS = 86_400_000
CHECKPOINT_SECONDS = 3600.0
SWEEP_SECONDS = 6 * 3600.0


class SentinelUnavailable(RuntimeError):
    pass


def _engine_class():
    return native_module.feature("RustSentinel")


def day_of(at: float) -> str:
    return datetime.fromtimestamp(at).strftime("%Y-%m-%d")


def day_bounds(day: str) -> tuple[int, int]:
    start = datetime.strptime(day, "%Y-%m-%d")
    end = start + timedelta(days=1)
    return int(start.timestamp() * 1000), int(end.timestamp() * 1000) - 1


class Journal:

    def __init__(self, clock=time.time) -> None:
        self.clock = clock
        self._lock = threading.RLock()
        self.engine = None
        self.heads: dict[str, tuple[str | None, int]] = {}
        self.signed_at: dict[str, float] = {}
        self.retention: str | None = None
        self.swept_at = 0.0

    def ready(self):
        with self._lock:
            if self.engine is None:
                engine = _engine_class()
                if engine is None:
                    raise SentinelUnavailable("sentinel.native.missing")
                if self.retention is None:
                    stored = vault.load_retention()
                    self.retention = json.dumps(stored) if stored else None
                self.engine = engine(vault.secret("master"), vault.secret("signing"), self.retention)
            return self.engine

    def configure(self, retention: dict | None) -> None:
        with self._lock:
            self.retention = json.dumps(retention) if retention else None
            self.engine = None
            self.ready()

    def _key(self, day: str) -> bytes:
        engine = self.ready()
        return vault.wrapped_key(day, engine.new_day_key)

    def _head(self, day: str) -> tuple[str | None, int]:
        if day in self.heads:
            return self.heads[day]
        data = vault.read_day(day)
        if not data:
            self.heads[day] = (None, 0)
            return self.heads[day]
        head, count, valid, torn = self.ready().verify(day, data)
        if torn:
            log.error("Diario Sentinella del %s con una scrittura interrotta: coda messa da parte", day)
            vault.set_aside(day, valid)
        self.heads[day] = (head, count)
        return self.heads[day]

    def append(self, event: dict) -> str:
        with self._lock:
            at = event["at_ms"] / 1000
            day = day_of(at)
            wrapped = self._key(day)
            prev, count = self._head(day)
            frame, head = self.ready().append(wrapped, day, prev, json.dumps(event, ensure_ascii=False))
            vault.append_day(day, bytes(frame))
            self.heads[day] = (head, count + 1)
            self._maybe_sign(day)
            self._maybe_sweep()
            return event["id"]

    def _maybe_sweep(self) -> None:
        now = self.clock()
        if now - self.swept_at < SWEEP_SECONDS:
            return
        self.swept_at = now
        threading.Thread(target=self._sweep_logged, name="sentinel-sweep", daemon=True).start()

    def _sweep_logged(self) -> None:
        try:
            self.sweep()
        except (OSError, ValueError, SentinelUnavailable) as exc:
            log.error("Pulizia della Sentinella non riuscita: %s", exc)

    def _maybe_sign(self, day: str, force: bool = False) -> None:
        now = self.clock()
        if not force and now - self.signed_at.get(day, 0.0) < CHECKPOINT_SECONDS:
            return
        head, count = self.heads.get(day, (None, 0))
        if head is None:
            return
        signature = bytes(self.ready().checkpoint(day, count, head))
        vault.write_checkpoint(day, json.dumps({"count": count, "head": head, "sig": signature.hex()}).encode())
        self.signed_at[day] = now

    def integrity(self, day: str) -> dict:
        with self._lock:
            data = vault.read_day(day)
            head, count, _, torn = self.ready().verify(day, data) if data else (None, 0, 0, False)
            raw = vault.read_checkpoint(day)
            if raw is None:
                return {"day": day, "count": count, "chain": True, "signed": None, "torn": torn}
            mark = json.loads(raw)
            signed = bool(self.ready().verify_checkpoint(day, int(mark["count"]), str(mark["head"]),
                                                          bytes.fromhex(str(mark["sig"]))))
            covered = int(mark["count"]) <= count
            return {"day": day, "count": count, "chain": True, "signed": signed and covered, "torn": torn}

    def _days_between(self, from_ms: int, to_ms: int) -> list[str]:
        first = datetime.fromtimestamp(from_ms / 1000).date()
        last = datetime.fromtimestamp(to_ms / 1000).date()
        span = (last - first).days
        if span < 0 or span > 31:
            raise ValueError("sentinel.query.span")
        wanted = {(first + timedelta(days=n)).isoformat() for n in range(span + 1)}
        return [d for d in vault.days() if d in wanted]

    def query(self, query: dict) -> dict:
        with self._lock:
            days = [(self._key(d), d, vault.read_day(d)) for d in self._days_between(query["from_ms"], query["to_ms"])]
            return json.loads(self.ready().query(json.dumps(query), days))

    def delete(self, from_ms: int, to_ms: int, subject: str | None = None) -> int:
        removed = 0
        with self._lock:
            for day in self._days_between(from_ms, to_ms):
                wrapped = self._key(day)
                opened = json.loads(self.ready().open(wrapped, day, vault.read_day(day)))
                kept = [e for e in opened["events"]
                        if not (from_ms <= e["at_ms"] <= to_ms and (subject is None or _subject_key(e) == subject))]
                removed += opened["count"] - len(kept)
                self._rewrite(day, wrapped, kept)
        return removed

    def _rewrite(self, day: str, wrapped: bytes, events: list[dict]) -> None:
        engine = self.ready()
        head, data = None, bytearray()
        for event in events:
            frame, head = engine.append(wrapped, day, head, json.dumps(event, ensure_ascii=False))
            data += bytes(frame)
        vault.replace_day(day, bytes(data))
        self.heads[day] = (head, len(events))
        if head:
            self._maybe_sign(day, force=True)
        else:
            vault.checkpoint_path(day).unlink(missing_ok=True)

    def sweep(self) -> dict:
        now_ms = int(self.clock() * 1000)
        destroyed, trimmed = [], 0
        with self._lock:
            engine = self.ready()
            for day in vault.days():
                _, end = day_bounds(day)
                if engine.day_expired(end, now_ms):
                    vault.destroy(day)
                    self.heads.pop(day, None)
                    destroyed.append(day)
                    continue
                data = vault.read_day(day)
                if not data:
                    continue
                compacted, _, removed = engine.compact(self._key(day), day, data, now_ms)
                if removed:
                    vault.replace_day(day, bytes(compacted))
                    self.heads.pop(day, None)
                    if self._head(day)[0]:
                        self._maybe_sign(day, force=True)
                    else:
                        vault.checkpoint_path(day).unlink(missing_ok=True)
                    trimmed += removed
        if destroyed or trimmed:
            log.info("Sentinella: %d giorni cancellati, %d eventi scaduti rimossi", len(destroyed), trimmed)
        return {"destroyed": destroyed, "trimmed": trimmed}


def _subject_key(event: dict) -> str:
    subject = event.get("subject") or {}
    kind, ident = subject.get("type"), subject.get("id")
    return kind if ident is None else f"{kind}:{ident}"


def new_id() -> str:
    return secrets.token_hex(8)


journal = Journal()
