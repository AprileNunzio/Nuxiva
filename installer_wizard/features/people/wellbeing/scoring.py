import math
import threading
from collections import deque

FIELDS = ("width", "drop", "brow", "mimic")
FLOORS = {"width": 0.02, "drop": 0.02, "brow": 0.015, "mimic": 0.004}
WARM_SAMPLES = 40
ALPHA = 0.02
AREAS = ("tension", "exhaustion", "receptive", "relief")
SMOOTH_SECONDS = 20.0
MAX_AGE = 60.0


def _sigmoid(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-max(-12.0, min(12.0, x))))


class Baseline:

    def __init__(self, state: dict | None = None) -> None:
        state = state or {}
        self.mean = {f: state.get("mean", {}).get(f) for f in FIELDS}
        self.var = {f: state.get("var", {}).get(f, 0.0) for f in FIELDS}
        self.count = int(state.get("count", 0))

    def update(self, raw: dict) -> None:
        for field in FIELDS:
            value = raw.get(field)
            if not isinstance(value, (int, float)):
                continue
            if self.mean[field] is None:
                self.mean[field] = float(value)
                continue
            delta = value - self.mean[field]
            self.mean[field] += ALPHA * delta
            self.var[field] = (1 - ALPHA) * (self.var[field] + ALPHA * delta * delta)
        self.count += 1

    def z(self, field: str, value) -> float:
        if not isinstance(value, (int, float)) or self.mean[field] is None:
            return 0.0
        spread = max(math.sqrt(self.var[field]), FLOORS[field])
        return max(-4.0, min(4.0, (value - self.mean[field]) / spread))

    @property
    def warm(self) -> bool:
        return self.count >= WARM_SAMPLES

    def export(self) -> dict:
        return {"mean": self.mean, "var": self.var, "count": self.count}


def classify(arousal: float, valence: float) -> str:
    if arousal >= 66 or (arousal >= 55 and valence <= -0.35):
        return "tension"
    if arousal <= 28 and valence <= 0.15:
        return "exhaustion"
    if valence >= 0.25:
        return "relief"
    return "receptive"


def score(raw: dict, baseline: Baseline) -> dict:
    brow = _sigmoid(baseline.z("brow", raw.get("brow")))
    mimic = _sigmoid(baseline.z("mimic", raw.get("mimic")))
    valence = math.tanh((baseline.z("width", raw.get("width")) - baseline.z("drop", raw.get("drop"))) / 3.0)
    arousal = 100.0 * (0.5 * brow + 0.25 * mimic + 0.25 * (1.0 - (valence + 1.0) / 2.0))
    return {"arousal": round(arousal, 1), "valence": round(valence, 3), "brow_tension": round(brow, 3),
            "mimic": round(mimic, 3), "lip_tone": round(valence, 3), "area": classify(arousal, valence)}


class LiveMeter:

    def __init__(self) -> None:
        self._baselines: dict[str, Baseline] = {}
        self._recent: dict[str, deque] = {}
        self._lock = threading.Lock()

    def load(self, slug: str, state: dict | None) -> None:
        with self._lock:
            self._baselines[slug] = Baseline(state)

    def baseline(self, slug: str) -> Baseline:
        with self._lock:
            return self._baselines.setdefault(slug, Baseline())

    def ingest(self, slug: str, raw: dict, now: float) -> dict:
        base = self.baseline(slug)
        reading = score(raw, base)
        calibrating = not base.warm
        base.update(raw)
        reading["calibrating"] = calibrating
        reading["at"] = now
        with self._lock:
            window = self._recent.setdefault(slug, deque(maxlen=200))
            window.append(reading)
        return reading

    def live(self, slug: str, now: float) -> dict | None:
        with self._lock:
            window = [r for r in self._recent.get(slug, ()) if now - r["at"] <= SMOOTH_SECONDS]
            newest = self._recent.get(slug, [None])[-1] if self._recent.get(slug) else None
        if not window or newest is None or now - newest["at"] > MAX_AGE:
            return None
        arousal = sum(r["arousal"] for r in window) / len(window)
        valence = sum(r["valence"] for r in window) / len(window)
        return {"arousal": round(arousal, 1), "valence": round(valence, 3), "area": classify(arousal, valence),
                "brow_tension": round(sum(r["brow_tension"] for r in window) / len(window), 3),
                "mimic": round(sum(r["mimic"] for r in window) / len(window), 3), "lip_tone": round(valence, 3),
                "calibrating": newest["calibrating"], "samples": len(window), "at": newest["at"]}

    def forget(self, slug: str) -> None:
        with self._lock:
            self._baselines.pop(slug, None)
            self._recent.pop(slug, None)


meter = LiveMeter()
