import logging
import threading
import time

from config import env_get

from features.people.vitals.book import book
from features.people.vitals.consent import consent
from features.people.vitals.live import live

log = logging.getLogger("nuxiva.vitals.camera")
SETTING = "NUXIVA_RPPG"
KIND = "camera"
SOURCE = "webcam"
BAND_CACHE = 30.0
OTHER_FRESH = 900.0
INGEST_EVERY = 10.0
SEEN_TTL = 15.0
MAX_TARGETS = 4
LIMITS = {"heart_rate": (40, 180), "resp_rate": (5, 40)}
QUALITY = {"heart_rate": "hr_quality", "resp_rate": "rr_quality"}
READING_FRESH = 5.0


def enabled() -> bool:
    return env_get(SETTING, "1").strip().lower() not in ("0", "off", "no", "false")


def server_busy() -> bool:
    try:
        from features.governor.service import governor
    except ImportError:
        return False
    return bool(governor.enabled() and governor.pressure.high)


class CameraVitals:

    def __init__(self) -> None:
        self._bands: dict[str, tuple[bool, float]] = {}
        self._sent: dict[tuple[str, str], float] = {}
        self._seen: dict[str, dict] = {}
        self._forced: dict[str, float] = {}
        self._cost = {"cpu_ms": 0.0, "frames": 0}
        self._lock = threading.Lock()

    def has_band(self, slug: str, now: float | None = None) -> bool:
        now = now or time.time()
        cached = self._bands.get(slug)
        if cached and now - cached[1] < BAND_CACHE:
            return cached[0]
        linked = any(d.get("enabled", True) for d in book.of(slug))
        other = live.latest(slug, now).get("heart_rate")
        if other and other.get("kind") != KIND and other.get("age", OTHER_FRESH) < OTHER_FRESH:
            linked = True
        self._bands[slug] = (linked, now)
        return linked

    def forget(self, slug: str) -> None:
        self._bands.pop(slug, None)
        consent.forget(slug)

    def force(self, slug: str, seconds: float, now: float | None = None) -> None:
        now = now or time.time()
        with self._lock:
            self._forced = {k: v for k, v in self._forced.items() if v > now}
            if seconds > 0:
                self._forced[slug] = now + min(seconds, 300.0)
            else:
                self._forced.pop(slug, None)

    def forced(self, slug: str, now: float | None = None) -> bool:
        return self._forced.get(slug, 0.0) > (now or time.time())

    def reading(self, slug: str, now: float | None = None) -> dict | None:
        now = now or time.time()
        with self._lock:
            seen = self._seen.get(slug)
        return dict(seen) if seen and now - seen["at"] <= READING_FRESH else None

    def targets(self, visible: list, now: float | None = None) -> list[str]:
        now = now or time.time()
        if not enabled() or server_busy():
            return []
        slugs = []
        for person in visible:
            slug = person.get("slug")
            if not person.get("known") or not isinstance(slug, str) or slug in slugs or not consent.allowed(slug, now):
                continue
            if self.forced(slug, now) or not self.has_band(slug, now):
                slugs.append(slug)
        return slugs[:MAX_TARGETS]

    def _samples(self, slug: str, reading: dict, now: float) -> list[dict]:
        at = reading.get("at")
        if isinstance(at, bool) or not isinstance(at, (int, float)) or not now - READING_FRESH <= at <= now + 1.0:
            return []
        samples = []
        for metric, (low, high) in LIMITS.items():
            value = reading.get(metric)
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not low <= value <= high:
                continue
            if now - self._sent.get((slug, metric), 0.0) < INGEST_EVERY:
                continue
            self._sent[(slug, metric)] = now
            samples.append({"metric": metric, "value": value, "ts": min(float(at), now)})
        return samples

    def ingest(self, visible: list, cost: dict | None, wanted: list[str], now: float | None = None) -> int:
        now = now or time.time()
        from features.people.vitals import service
        accepted = 0
        for person in visible:
            slug, reading = person.get("slug"), person.get("vitals")
            if slug not in wanted or not isinstance(reading, dict):
                continue
            progress = reading.get("progress")
            with self._lock:
                self._seen[slug] = {"at": now, "progress": float(progress) if isinstance(progress, (int, float)) else 0.0,
                                    "quality": {m: reading.get(q) for m, q in QUALITY.items() if isinstance(reading.get(q), (int, float))},
                                    "values": {m: reading.get(m) for m, (lo, hi) in LIMITS.items()
                                               if isinstance(reading.get(m), int) and not isinstance(reading.get(m), bool) and lo <= reading[m] <= hi}}
            samples = self._samples(slug, reading, now)
            if samples:
                accepted += service.ingest(slug, samples, SOURCE, KIND, now)["accepted"]
        self._account(cost)
        return accepted

    def _account(self, cost: dict | None) -> None:
        if not isinstance(cost, dict):
            return
        cpu, frames = cost.get("cpu_ms"), cost.get("frames")
        if not isinstance(cpu, (int, float)) or not isinstance(frames, int) or isinstance(frames, bool):
            return
        previous, self._cost = self._cost, {"cpu_ms": float(cpu), "frames": frames}
        spent, count = float(cpu) - previous["cpu_ms"], frames - previous["frames"]
        if spent <= 0 or count <= 0:
            return
        try:
            from features.governor.service import governor
            if governor.enabled():
                governor.ledger.record("vision:rppg", "realtime", spent, spent, count)
        except ImportError:
            log.debug("Governatore non disponibile")

    def status(self, slug: str, now: float | None = None) -> dict:
        now = now or time.time()
        with self._lock:
            seen = self._seen.get(slug)
        recent = bool(seen and now - seen["at"] <= SEEN_TTL)
        values = live.latest(slug, now)
        streaming = any(v.get("kind") == KIND and v.get("age", SEEN_TTL * 10) <= 120 for v in values.values())
        if not enabled():
            state = "off"
        elif not consent.allowed(slug, now):
            state = "denied"
        elif self.has_band(slug, now) and not self.forced(slug, now):
            state = "band"
        elif server_busy():
            state = "busy"
        elif recent and streaming:
            state = "streaming"
        elif recent:
            state = "measuring"
        else:
            state = "idle"
        return {"enabled": enabled(), "state": state, "progress": round(seen["progress"], 2) if recent else 0.0,
                "quality": seen["quality"] if recent else {}}


camera = CameraVitals()
