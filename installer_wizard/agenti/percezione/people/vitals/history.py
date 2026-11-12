import logging
import threading
import time
from datetime import datetime

from config import ETC_DIR, STATE_DIR
from sealed import SealedFile

from agenti.people.vitals.model import METRICS

log = logging.getLogger("nuxiva.vitals.history")
DAYS = 120
MAX_MONTHS = 600
SAVE_EVERY = 60.0
MAX_PEOPLE = 64


def day_of(ts: float) -> str:
    return datetime.fromtimestamp(ts).strftime("%Y-%m-%d")


class History:
    def __init__(self, vault: SealedFile) -> None:
        self.vault = vault
        self._data: dict | None = None
        self._dirty = False
        self._saved = 0.0
        self._lock = threading.Lock()

    def _all(self) -> dict:
        if self._data is None:
            try:
                loaded = self.vault.load()
            except Exception as exc:
                log.warning("Storico della salute non leggibile, riparto da zero: %s", type(exc).__name__)
                loaded = {}
            self._data = loaded if isinstance(loaded, dict) else {}
        return self._data

    def record(self, slug: str, sample: dict, source: str, kind: str, now: float | None = None) -> None:
        now = now or time.time()
        metric, value, ts = sample["metric"], float(sample["value"]), float(sample["ts"])
        with self._lock:
            data = self._all()
            if slug not in data and len(data) >= MAX_PEOPLE:
                return
            person = data.setdefault(slug, {"days": {}, "last": {}})
            cell = person["days"].setdefault(day_of(ts), {}).setdefault(metric, {"n": 0, "sum": 0.0, "min": value, "max": value, "last": value, "ts": ts})
            cell["n"] += 1
            cell["sum"] += value
            cell["min"], cell["max"] = min(cell["min"], value), max(cell["max"], value)
            if ts >= cell["ts"]:
                cell["last"], cell["ts"] = value, ts
            known = person["last"].get(metric)
            if not known or ts >= known["ts"]:
                person["last"][metric] = {"value": sample["value"], "ts": ts, "source": source, "kind": kind}
            self._dirty = True
            self._trim(person)
        self.flush(now)

    @staticmethod
    def _trim(person: dict) -> None:
        days = sorted(person["days"])
        months = person.setdefault("months", {})
        for old in days[:-DAYS]:
            bucket = months.setdefault(old[:7], {})
            for metric, cell in person["days"].pop(old).items():
                kept = bucket.get(metric)
                if kept is None:
                    bucket[metric] = {"n": cell["n"], "sum": cell["sum"], "min": cell["min"], "max": cell["max"], "days": 1}
                else:
                    kept["n"] += cell["n"]
                    kept["sum"] += cell["sum"]
                    kept["min"], kept["max"] = min(kept["min"], cell["min"]), max(kept["max"], cell["max"])
                    kept["days"] = kept.get("days", 1) + 1
        for old in sorted(months)[:-MAX_MONTHS]:
            del months[old]

    def months(self, slug: str, metric: str) -> list[dict]:
        spec = METRICS.get(metric)
        if not spec:
            return []
        with self._lock:
            months = dict((self._all().get(slug) or {}).get("months") or {})
        out = []
        for month in sorted(months):
            cell = months[month].get(metric)
            if cell:
                value = cell["max"] if spec.get("daily") else cell["sum"] / max(1, cell["n"])
                out.append({"month": month, "value": round(value, spec["digits"]) if spec["digits"] else int(round(value))})
        return out

    def span(self, slug: str) -> dict:
        with self._lock:
            person = self._all().get(slug) or {}
            keys = sorted(person.get("days") or {}) + [f"{m}-01" for m in person.get("months") or {}]
        return {"since": min(keys) if keys else None, "days": len(person.get("days") or {}), "months": len(person.get("months") or {})}

    def flush(self, now: float | None = None, force: bool = False) -> None:
        now = now or time.time()
        with self._lock:
            if not self._dirty or (not force and now - self._saved < SAVE_EVERY):
                return
            snapshot = dict(self._all())
            self._dirty, self._saved = False, now
        try:
            self.vault.save(snapshot)
        except OSError as exc:
            log.warning("Storico della salute non salvato: %s", exc)
            self._dirty = True

    def last_known(self, slug: str, now: float | None = None) -> dict:
        now = now or time.time()
        with self._lock:
            rows = dict((self._all().get(slug) or {}).get("last") or {})
        out = {}
        for metric, row in rows.items():
            spec = METRICS.get(metric)
            if spec and now - row["ts"] <= spec["fresh"]:
                out[metric] = {"value": row["value"], "ts": row["ts"], "age": round(max(0.0, now - row["ts"]), 1), "source": row["source"],
                               "kind": row["kind"], "unit": spec["unit"]}
        return out

    def trend(self, slug: str, metric: str, days: int = 7, now: float | None = None) -> list[dict]:
        now = now or time.time()
        spec = METRICS.get(metric)
        if not spec:
            return []
        with self._lock:
            person = (self._all().get(slug) or {}).get("days") or {}
            out = []
            for back in range(days - 1, -1, -1):
                day = day_of(now - back * 86400)
                cell = (person.get(day) or {}).get(metric)
                value = None
                if cell:
                    value = cell["max"] if spec.get("daily") else cell["sum"] / max(1, cell["n"])
                    value = round(value, spec["digits"]) if spec["digits"] else int(round(value))
                out.append({"day": day, "value": value})
        return out

    def baseline(self, slug: str, metric: str, now: float | None = None, days: int = 14) -> float | None:
        values = [d["value"] for d in self.trend(slug, metric, days + 1, now)[:-1] if d["value"] is not None]
        return sum(values) / len(values) if len(values) >= 3 else None

    def forget(self, slug: str) -> None:
        with self._lock:
            if self._all().pop(slug, None) is not None:
                self._dirty = True
        self.flush(force=True)


history = History(SealedFile(STATE_DIR / "vitals_history.vault", ETC_DIR / "vitals_history.key"))
