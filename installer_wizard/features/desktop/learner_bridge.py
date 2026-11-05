import json
import logging
import os
import re
import threading
import time
from datetime import datetime

from features.desktop import learner_store
from features.desktop.privacy import flag

log = logging.getLogger("nuxiva.desktop.learner")
WIDGET = re.compile(r"^[a-z0-9_-]{1,64}$")
QUICK_SECONDS = 3.0
INTERACT_THROTTLE = 5.0
SAVE_EVERY = 30.0
MAX_SEEN = 512
SIZES = frozenset({"s", "m", "l", "xl", "full"})
AUDIO = frozenset({"music", "karaoke", "tv_player", "audio_spectrum"})
BROWSER_KINDS = frozenset({"interact", "dwell"})


def _native_class():
    if os.environ.get("NUXIVA_NATIVE", "auto").strip() == "0":
        return None
    try:
        import nuxiva_native
    except ImportError:
        return None
    return getattr(nuxiva_native, "RustLearner", None)


def enabled() -> bool:
    return flag("NUXIVA_DISPLAY_LEARNING", True)


def context_vector(now: float, screen: int, mode: str, crowd: int, items: list[dict]) -> dict:
    moment = datetime.fromtimestamp(now)
    media = any(i.get("id") in AUDIO for i in items)
    activity = mode if mode in ("conversation", "project") else ("media" if media else "ambient")
    return {"band": moment.hour // 4, "weekend": moment.weekday() >= 5, "activity": activity,
            "crowd": max(0, min(2, int(crowd))), "role": "main" if screen == 0 else "side"}


def audience_of(last: dict) -> tuple[bool, str | None, bool, int]:
    kind = last.get("kind")
    members = [str(m.get("person")) for m in last.get("members") or [] if m.get("person")]
    crowd = len(members) + int(last.get("guests") or 0)
    if kind == "authorized" and len(members) == 1:
        return True, members[0], False, crowd
    if kind in ("mixed", "guest_only"):
        return True, None, True, crowd
    return False, None, False, crowd


class LearnerBridge:

    def __init__(self, clock=time.time) -> None:
        self.clock = clock
        self._lock = threading.RLock()
        self.engine = None
        self.key: bytes | None = None
        self.loaded = False
        self.seen: dict[str, dict] = {}
        self.closing: set[str] = set()
        self.saved_at = 0.0
        self.tick = 0
        self.mode = "ambient"
        self.had_guests = False

    def ready(self):
        if not enabled():
            return None
        with self._lock:
            if self.loaded:
                return self.engine
            self.loaded = True
            native = _native_class()
            if native is None:
                return None
            self.engine = native()
            self.key = learner_store.master()
            for person, blob in learner_store.stored():
                try:
                    self.engine.import_sealed(self.key, person, blob)
                except ValueError as exc:
                    log.error("Profilo di apprendimento illeggibile, messo da parte: %s", exc)
                    learner_store.quarantine(person)
            return self.engine

    def person(self, slug: str | None) -> str | None:
        if not slug or self.ready() is None or self.key is None:
            return None
        return learner_store.pseudonym(slug, self.key)

    def _who(self) -> tuple[bool, str | None, bool, int]:
        from features.desktop.presence_bridge import bridge
        ok, slug, guests, crowd = audience_of(bridge.last)
        return ok, self.person(slug), guests, crowd

    def _sample(self, item: dict, kind: str, now: float, **extra) -> None:
        engine = self.ready()
        wid = str(item.get("id") or "")
        if engine is None or not WIDGET.match(wid):
            return
        ok, person, guests, crowd = self._who()
        if not ok:
            return
        screen = item.get("screen") if isinstance(item.get("screen"), int) and item["screen"] >= 0 else 0
        sample = {"person": person, "widget": wid, "kind": kind, "at_ms": int(now * 1000), "guests": guests,
                  "urgency": 3 if item.get("urgent") else 0,
                  "context": context_vector(now, screen, self.mode, crowd, list(self.seen.values())), **extra}
        try:
            engine.observe(json.dumps(sample))
        except ValueError as exc:
            log.warning("Segnale di apprendimento scartato: %s", exc)
        self._persist(now)

    def observe_desk(self, items: list[dict], now: float | None = None) -> None:
        if self.ready() is None:
            return
        now = self.clock() if now is None else now
        with self._lock:
            guests = self._who()[2]
            if self.had_guests and not guests:
                self.guests_left()
            self.had_guests = guests
            current = {str(i.get("key")): i for i in items if i.get("key")}
            for key, item in current.items():
                if key not in self.seen:
                    self.seen[key] = {"id": item.get("id"), "screen": item.get("screen"), "urgent": item.get("urgent"),
                                      "shown_at": now, "interacted": False, "expires_at": item.get("expires_at")}
                    self._sample(item, "shown", now)
                    if item.get("intent"):
                        self._sample(item, "ask_show", now)
            for key in [k for k in self.seen if k not in current]:
                gone = self.seen.pop(key)
                if key in self.closing:
                    self.closing.discard(key)
                elif gone.get("expires_at") and gone["expires_at"] <= now and not gone["interacted"]:
                    self._sample(gone, "expired", now)
            while len(self.seen) > MAX_SEEN:
                self.seen.pop(next(iter(self.seen)))

    def closed(self, key: str) -> None:
        with self._lock:
            entry = self.seen.get(key)
            if entry is None:
                return
            now = self.clock()
            quick = now - entry["shown_at"] < QUICK_SECONDS and not entry["interacted"]
            self.closing.add(key)
            self._sample(entry, "quick_close" if quick else "closed_after_use", now)

    def interacted(self, key: str, kind: str = "interact") -> bool:
        if kind not in BROWSER_KINDS:
            return False
        with self._lock:
            entry = self.seen.get(key)
            now = self.clock()
            if entry is None or now - entry.get("touched_at", 0.0) < INTERACT_THROTTLE:
                return False
            entry["interacted"] = True
            entry["touched_at"] = now
            self._sample(entry, kind, now)
            return True

    def moved(self, wid: str, x: float, y: float) -> None:
        with self._lock:
            entry = next((e for e in self.seen.values() if e.get("id") == wid), None)
            if entry is not None:
                cell = [max(0, min(11, int(x * 12))), max(0, min(23, int(y * 24)))]
                self._sample(entry, "move", self.clock(), cell=cell)

    def resized(self, key: str, size: str) -> None:
        with self._lock:
            entry = self.seen.get(key)
            if entry is not None and size in SIZES:
                self._sample(entry, "resize", self.clock(), size=size)

    def preferences(self, widgets: list[str], screen: int, mode: str, items: list[dict], now: float) -> dict[str, float]:
        engine = self.ready()
        if engine is None:
            return {}
        ok, person, guests, crowd = self._who()
        if not ok:
            return {}
        wanted = sorted({w for w in widgets if WIDGET.match(w)})
        with self._lock:
            self.mode = mode
            self.tick += 1
            query = {"person": person, "guests": guests, "now_ms": int(now * 1000), "tick": self.tick, "widgets": wanted,
                     "context": context_vector(now, screen, mode, crowd, items)}
        try:
            return {w: float(a["value"]) for w, a in json.loads(engine.affinities(json.dumps(query))).items()}
        except ValueError as exc:
            log.error("Preferenze apprese non disponibili: %s", exc)
            return {}

    def interaction_ms(self, key: str, now: float) -> int | None:
        entry = self.seen.get(key)
        touched = entry.get("touched_at") if entry else None
        return int((now - touched) * 1000) if touched else None

    def _persist(self, now: float, force: bool = False) -> None:
        if self.engine is None or self.key is None or (not force and now - self.saved_at < SAVE_EVERY):
            return
        self.saved_at = now
        for person in self.engine.take_dirty():
            try:
                learner_store.save(person, bytes(self.engine.export_sealed(self.key, person)))
            except (OSError, ValueError) as exc:
                log.error("Profilo di apprendimento non salvato: %s", exc)

    def flush(self) -> None:
        with self._lock:
            self._persist(self.clock(), force=True)

    def guests_left(self) -> None:
        engine = self.ready()
        if engine is not None:
            engine.forget_session()

    def metrics(self, slug: str | None = None) -> dict:
        engine = self.ready()
        if engine is None:
            return {"engine": "off" if not enabled() else "missing", "enabled": enabled()}
        person = self.person(slug) if slug else None
        raw = engine.metrics(person) if slug else engine.metrics(None)
        data = json.loads(raw) if raw else None
        rates = None
        if data and data.get("shown", 0) > 0:
            rates = {"quick_close": round(data["quick_close"] / data["shown"], 3),
                     "interact_per_shown": round(data["interact"] / data["shown"], 3)}
        return {"engine": "rust", "enabled": True, "people": len(engine.persons()), "metrics": data, "rates": rates}

    def reset(self, slug: str) -> bool:
        engine = self.ready()
        if engine is None:
            return False
        person = self.person(slug)
        with self._lock:
            had = bool(engine.reset(person))
            return learner_store.delete(person) or had


bridge = LearnerBridge()
