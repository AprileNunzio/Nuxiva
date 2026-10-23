import threading
import time
from collections import deque

from features.people.vitals.model import METRICS, PRIORITY

KEEP = 240
FRESH_SECONDS = 120
TIE_WINDOW = 5.0


class Live:
    def __init__(self) -> None:
        self._rows: dict[str, dict[str, deque]] = {}
        self._lock = threading.Lock()

    def put(self, slug: str, sample: dict, source: str, kind: str, now: float | None = None) -> bool:
        now = now or time.time()
        row = (sample["ts"], sample["value"], source, kind)
        with self._lock:
            series = self._rows.setdefault(slug, {}).setdefault(sample["metric"], deque(maxlen=KEEP))
            if any(r[0] == row[0] and r[2] == source for r in series):
                return False
            series.append(row)
            ordered = sorted(series, key=lambda r: r[0])
            series.clear()
            series.extend(ordered)
        return True

    def latest(self, slug: str, now: float | None = None) -> dict:
        now = now or time.time()
        out = {}
        with self._lock:
            for metric, series in (self._rows.get(slug) or {}).items():
                fresh = [r for r in series if now - r[0] <= FRESH_SECONDS]
                if not fresh:
                    continue
                newest = max(r[0] for r in fresh)
                near = [r for r in fresh if newest - r[0] <= TIE_WINDOW]
                best = max(near, key=lambda r: (PRIORITY.get(r[3], 0), r[0]))
                out[metric] = {"value": best[1], "ts": best[0], "age": round(max(0.0, now - best[0]), 1), "source": best[2], "kind": best[3],
                               "unit": METRICS[metric]["unit"]}
        return out

    def series(self, slug: str, metric: str, count: int = 60) -> list[list[float]]:
        with self._lock:
            rows = list((self._rows.get(slug) or {}).get(metric) or [])
        return [[r[0], r[1]] for r in rows[-count:]]

    def forget(self, slug: str) -> None:
        with self._lock:
            self._rows.pop(slug, None)

    def prune(self, now: float | None = None, keep_seconds: float = 1800) -> None:
        now = now or time.time()
        with self._lock:
            for slug in list(self._rows):
                for metric in list(self._rows[slug]):
                    series = self._rows[slug][metric]
                    while series and now - series[0][0] > keep_seconds:
                        series.popleft()
                    if not series:
                        del self._rows[slug][metric]
                if not self._rows[slug]:
                    del self._rows[slug]


live = Live()
