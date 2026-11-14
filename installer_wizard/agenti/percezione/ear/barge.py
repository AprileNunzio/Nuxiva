import json
import logging
from pathlib import Path

log = logging.getLogger("nuxiva.ear.barge")
CATALOG = Path(__file__).with_name("backchannel.json")
VERDICTS = ("known", "guest", "broadcast", "uncertain")
DEFAULTS = {"min_voiced_ms": 250, "duck_after_ms": 100, "duck_ms": 3000, "min_margin_permille": 600, "guest_may_interrupt": True, "cooldown_ms": 400, "pre_roll_ms": 600}


def native():
    try:
        import nuxiva_native
    except ImportError:
        return None
    return getattr(nuxiva_native, "RustBarge", None)


def may_command(verdict: str, risk: str) -> bool:
    return verdict == "known" or (verdict == "guest" and risk == "low")


class PyBarge:
    def __init__(self, settings_json: str = ""):
        self._cfg = {**DEFAULTS, **(json.loads(settings_json) if settings_json else {})}
        catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
        self._max_words, self._fillers = catalog["max_words"], {f.lower() for f in catalog["fillers"]}
        self._voiced, self._ducked, self._cooldown = 0, None, 0
        self._stats = {"cuts": 0, "ducks": 0, "ignored_broadcast": 0, "ignored_uncertain": 0, "ignored_guest": 0, "ignored_weak": 0}

    def _eligible(self, verdict: str, margin: int) -> bool:
        if verdict not in VERDICTS:
            raise ValueError("duplex.invalid")
        if verdict in ("broadcast", "uncertain"):
            self._stats[f"ignored_{verdict}"] += 1
            return False
        if verdict == "guest" and not self._cfg["guest_may_interrupt"]:
            self._stats["ignored_guest"] += 1
            return False
        if margin < self._cfg["min_margin_permille"]:
            self._stats["ignored_weak"] += 1
            return False
        return True

    def _restore(self, now: int) -> str:
        if self._ducked is not None and now - self._ducked >= self._cfg["duck_ms"]:
            self._ducked = None
            return json.dumps({"decision": "restore"})
        return json.dumps({"decision": "hold"})

    def step(self, duplex, verdict: str, margin: int, voiced: bool, frame_ms: int, now: int) -> str:
        if json.loads(duplex.snapshot())["state"] != "speaking":
            self._voiced, self._ducked = 0, None
            return json.dumps({"decision": "hold"})
        if not voiced or not self._eligible(verdict, margin):
            self._voiced = 0
            return self._restore(now)
        self._voiced += frame_ms
        if self._voiced >= self._cfg["min_voiced_ms"] and now >= self._cooldown:
            self._voiced, self._ducked = 0, None
            try:
                report = json.loads(duplex.cut(0, now))
            except ValueError:
                return json.dumps({"decision": "hold"})
            self._cooldown = now + self._cfg["cooldown_ms"]
            self._stats["cuts"] += 1
            return json.dumps({"decision": "cut", "report": report})
        if self._voiced >= self._cfg["duck_after_ms"] and self._ducked is None:
            self._ducked = now
            self._stats["ducks"] += 1
            return json.dumps({"decision": "duck"})
        return json.dumps({"decision": "hold"})

    def tick(self, now: int) -> str:
        return self._restore(now)

    def is_backchannel(self, text: str) -> bool:
        words = [w for w in (t.strip("".join(c for c in t if not (c.isalnum() or c == "'"))).lower() for t in text.split()) if w]
        return bool(words) and len(words) <= self._max_words and all(w in self._fillers for w in words)

    def stats(self) -> str:
        return json.dumps(self._stats)


class PyPreRoll:
    def __init__(self, rate_hz: int, ms: int, bytes_per_sample: int):
        if not 8000 <= rate_hz <= 96000 or not 1 <= bytes_per_sample <= 4 or not 100 <= ms <= 5000:
            raise ValueError("duplex.settings.invalid")
        self._cap = rate_hz * ms * bytes_per_sample // 1000
        self._buf = bytearray()

    def push(self, pcm: bytes) -> None:
        self._buf += pcm[-self._cap:]
        del self._buf[:-self._cap]

    def snapshot(self) -> bytes:
        return bytes(self._buf)

    def clear(self) -> None:
        self._buf.clear()


def build(settings_json: str = ""):
    klass = native()
    return klass(settings_json) if klass is not None else PyBarge(settings_json)
