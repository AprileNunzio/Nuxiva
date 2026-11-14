import json
import logging
import threading
import time

log = logging.getLogger("nuxiva.ear.duplex")
SETTINGS = {
    "max_audio_bytes": 4096, "max_text_bytes": 4096, "rate_per_second": 100, "rate_burst": 200, "max_cancel_tokens": 64,
    "event_cap": 256, "fade_ms": 30, "listening_ms": 30000, "thinking_ms": 60000, "speaking_ms": 300000, "interrupted_ms": 2000,
}
TABLE = {
    ("idle", "voice_start"): "listening", ("thinking", "voice_start"): "listening", ("listening", "voice_end"): "thinking",
    ("idle", "reply_start"): "speaking", ("thinking", "reply_start"): "speaking", ("speaking", "reply_end"): "idle",
    ("speaking", "interrupt"): "interrupted", ("interrupted", "resume"): "listening",
}
TIMEOUT = {"idle": None, "listening": "idle", "thinking": "idle", "speaking": "idle", "interrupted": "listening"}
_lock = threading.Lock()
_session = {"obj": None}


def native():
    try:
        import nuxiva_native
    except ImportError:
        return None
    return getattr(nuxiva_native, "RustDuplex", None)


def now_ms() -> int:
    return int(time.time() * 1000)


class PyFlag:
    def __init__(self):
        self._set = threading.Event()

    def is_cancelled(self) -> bool:
        return self._set.is_set()

    def cancel(self) -> None:
        self._set.set()


class PyDuplex:
    def __init__(self, settings_json: str = "", now: int = 0):
        self._cfg = {**SETTINGS, **(json.loads(settings_json) if settings_json else {})}
        self._state, self._entered, self._epoch, self._cut, self._out, self._spoken = "idle", now, 0, 0, 0, 0
        self._last: dict[int, int] = {}
        self._flags: list[tuple[int, PyFlag]] = []
        self._note = None
        self._events: list[dict] = []
        self._bucket = self._cfg["rate_burst"] * 1000
        self._refilled = now

    def _record(self, at: int, kind: str, epoch: int) -> None:
        self._events = (self._events + [{"at_ms": at, "kind": kind, "gen": epoch, "state": self._state}])[-self._cfg["event_cap"]:]

    def _enter(self, state: str, now: int, kind: str) -> None:
        self._state, self._entered = state, now
        self._record(now, kind, self._epoch)

    def _release(self) -> None:
        for _, flag in self._flags:
            flag.cancel()
        self._flags = []
        self._cut = self._epoch

    def trigger(self, code: str, now: int) -> str:
        if code == "interrupt":
            if self._state != "speaking":
                raise ValueError("duplex.transition")
            return json.loads(self.cut(0, now))["state"] and json.dumps(self._state)
        if code == "reset":
            self._release()
            self._enter("idle", now, "transition")
            return json.dumps("idle")
        nxt = TABLE.get((self._state, code))
        if nxt is None:
            raise ValueError("duplex.transition" if code in {c for _, c in TABLE} else "duplex.invalid")
        self._enter(nxt, now, "transition")
        return json.dumps(nxt)

    def begin_reply(self, now: int) -> int:
        if TABLE.get((self._state, "reply_start")) is None:
            raise ValueError("duplex.transition")
        if self._epoch >= 0xFFFFFFFF:
            raise ValueError("duplex.capacity")
        self._epoch += 1
        self._out, self._spoken, self._note = 0, 0, None
        self._enter("speaking", now, "transition")
        return self._epoch

    def _current(self, epoch: int) -> None:
        if epoch != self._epoch or epoch <= self._cut:
            raise ValueError("duplex.stale")

    def next_seq(self, epoch: int) -> int:
        self._current(epoch)
        self._out += 1
        return self._out

    def bind(self, epoch: int) -> PyFlag:
        flag = PyFlag()
        if epoch <= self._cut or epoch > self._epoch:
            flag.cancel()
            raise ValueError("duplex.stale")
        if len(self._flags) >= self._cfg["max_cancel_tokens"]:
            raise ValueError("duplex.capacity")
        self._flags.append((epoch, flag))
        return flag

    def mark_spoken(self, epoch: int, chars: int) -> None:
        self._current(epoch)
        self._spoken += chars

    def admit(self, epoch: int, seq: int, now: int) -> None:
        elapsed = max(0, now - self._refilled)
        self._refilled = max(self._refilled, now)
        self._bucket = min(self._cfg["rate_burst"] * 1000, self._bucket + elapsed * self._cfg["rate_per_second"])
        if self._bucket < 1000:
            self._record(now, "rate_limited", epoch)
            raise ValueError("duplex.rate_limited")
        self._bucket -= 1000
        if epoch != 0 and epoch <= self._cut:
            self._record(now, "stale", epoch)
            raise ValueError("duplex.stale")
        if epoch in self._last and seq <= self._last[epoch]:
            raise ValueError("duplex.sequence")
        floor = max(0, self._epoch - 8)
        self._last = {e: s for e, s in self._last.items() if e == 0 or e >= floor}
        self._last[epoch] = seq

    def cut(self, epoch: int, now: int) -> str:
        target = self._epoch if epoch == 0 else epoch
        if target > self._epoch:
            raise ValueError("duplex.invalid")
        self._cut = max(self._cut, target)
        kept = [(e, f) for e, f in self._flags if e > self._cut]
        cancelled = len(self._flags) - len(kept)
        for e, f in self._flags:
            if e <= self._cut:
                f.cancel()
        self._flags = kept
        note = None
        if self._state == "speaking" and target == self._epoch:
            note = {"gen": target, "spoken_chars": self._spoken, "at_ms": now, "fade_ms": self._cfg["fade_ms"]}
            self._note = note
            self._enter("interrupted", now, "cut")
        else:
            self._record(now, "cut", target)
        return json.dumps({"gen": target, "cancelled": cancelled, "state": self._state, "interruption": note})

    def finish(self, epoch: int, now: int) -> str:
        self._current(epoch)
        self._flags = [(e, f) for e, f in self._flags if e != epoch]
        return self.trigger("reply_end", now)

    def tick(self, now: int):
        limit = {"listening": "listening_ms", "thinking": "thinking_ms", "speaking": "speaking_ms", "interrupted": "interrupted_ms"}.get(self._state)
        if limit is None or now - self._entered < self._cfg[limit]:
            return None
        nxt = TIMEOUT[self._state]
        if self._state in ("speaking", "thinking"):
            self._release()
        self._enter(nxt, now, "timeout")
        return json.dumps(nxt)

    def is_live(self, epoch: int) -> bool:
        return epoch > self._cut

    def snapshot(self) -> str:
        return json.dumps({"state": self._state, "gen": self._epoch, "cut_upto": self._cut, "bound_tokens": len(self._flags), "spoken_chars": self._spoken})

    def interruption(self) -> str:
        return json.dumps(self._note)

    def events(self) -> str:
        out, self._events = self._events, []
        return json.dumps(out)


def build(settings_json: str = "", now: int | None = None):
    klass = native()
    start = now_ms() if now is None else now
    if klass is not None:
        return klass(settings_json, start)
    return PyDuplex(settings_json, start)


def get():
    with _lock:
        if _session["obj"] is None:
            _session["obj"] = build()
        return _session["obj"]


def reset() -> None:
    with _lock:
        _session["obj"] = None
