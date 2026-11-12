import asyncio
import logging
import re
import time
from datetime import datetime, timedelta, timezone

import httpx

from agenti.people.sync_board import board
from agenti.medico.vitals.history import history
from agenti.medico.vitals.journal import journal
from agenti.medico.vitals.live import live
from agenti.medico.vitals.model import clean_sample

log = logging.getLogger("nuxiva.vitals.cloud")
BASE = "https://health.googleapis.com/v4/users/me/dataTypes"
SERVICE = "health"
ACTIVITY = "health_activity"
WINDOW = timedelta(minutes=10)
MIN_GAP = 60.0
SOURCES = (
    ("heart-rate", "heartRate", "beatsPerMinute", "heart_rate", 1.0, WINDOW),
    ("oxygen-saturation", "oxygenSaturation", "percentage", "spo2", 1.0, timedelta(hours=6)),
    ("core-body-temperature", "coreBodyTemperature", "temperatureCelsius", "body_temp", 1.0, timedelta(hours=6)),
    ("heart-rate-variability", "heartRateVariability", "rootMeanSquareOfSuccessiveDifferencesMilliseconds", "hrv", 1.0, timedelta(hours=36)),
    ("blood-glucose", "bloodGlucose", "bloodGlucoseMilligramsPerDeciliter", "glucose", 1.0, timedelta(hours=12)),
    ("weight", "weight", "weightGrams", "weight", 0.001, timedelta(days=30)),
)
DAILY_WINDOW = timedelta(hours=36)
STAGES = {"DEEP": "sleep_deep_min", "REM": "sleep_rem_min"}
_state: dict[str, dict] = {}
_locks: dict[str, asyncio.Lock] = {}


def status(slug: str) -> dict:
    return dict(_state.get(slug) or {"state": "idle", "at": 0.0, "error": ""})


def parse_time(node) -> float | None:
    raw = (node or {}).get("physicalTime") if isinstance(node, dict) else None
    try:
        return datetime.fromisoformat(str(raw).replace("Z", "+00:00")).timestamp()
    except ValueError:
        return None


def points(body: dict, key: str, field: str, metric: str, now: float, scale: float = 1.0) -> list[dict]:
    out = []
    for item in (body.get("dataPoints") or []) if isinstance(body, dict) else []:
        inner = item.get(key) if isinstance(item, dict) else None
        if not isinstance(inner, dict):
            continue
        ts = parse_time(inner.get("sampleTime"))
        try:
            out.append(clean_sample({"metric": metric, "value": float(inner.get(field)) * scale, "ts": ts if ts is not None else now}, now))
        except (TypeError, ValueError):
            continue
    return out


def parse_instant(raw) -> float | None:
    try:
        return datetime.fromisoformat(str(raw).replace("Z", "+00:00")).timestamp()
    except ValueError:
        return None


def _rows(body: dict, key: str) -> list[dict]:
    items = (body.get("dataPoints") or []) if isinstance(body, dict) else []
    return [i[key] for i in items if isinstance(i, dict) and isinstance(i.get(key), dict)]


def _safe(metric: str, value, ts: float, now: float) -> list[dict]:
    try:
        return [clean_sample({"metric": metric, "value": value, "ts": ts}, now)]
    except (TypeError, ValueError):
        return []


def steps_today(body: dict, now: float) -> list[dict]:
    midnight = datetime.fromtimestamp(now).replace(hour=0, minute=0, second=0, microsecond=0).timestamp()
    total, seen = 0, False
    for row in _rows(body, "steps"):
        start = parse_instant((row.get("interval") or {}).get("startTime"))
        try:
            count = int(row.get("count"))
        except (TypeError, ValueError):
            continue
        if start is not None and start >= midnight and 0 <= count <= 1_000_000:
            total, seen = total + count, True
    return _safe("steps", total, now, now) if seen else []


def last_sleep(body: dict, now: float) -> list[dict]:
    nights = []
    for row in _rows(body, "sleep"):
        end = parse_instant((row.get("interval") or {}).get("endTime"))
        summary = row.get("summary") if isinstance(row.get("summary"), dict) else {}
        if end is not None and summary.get("minutesAsleep") is not None:
            nights.append((end, summary))
    if not nights:
        return []
    end, summary = max(nights, key=lambda n: n[0])
    out = _safe("sleep_min", summary.get("minutesAsleep"), end, now)
    for stage in summary.get("stagesSummary") or []:
        metric = STAGES.get(str((stage or {}).get("type", "")).upper()) if isinstance(stage, dict) else None
        if metric:
            out += _safe(metric, stage.get("minutes"), end, now)
    return out


def resting_today(body: dict, now: float) -> list[dict]:
    best = None
    for row in _rows(body, "dailyRestingHeartRate"):
        date = row.get("date") if isinstance(row.get("date"), dict) else {}
        try:
            ts = datetime(int(date["year"]), int(date["month"]), int(date["day"]), 12).timestamp()
        except (KeyError, TypeError, ValueError):
            continue
        if best is None or ts > best[0]:
            best = (ts, row.get("beatsPerMinute"))
    return _safe("resting_hr", best[1], min(best[0], now), now) if best else []


DAILY = (
    ("steps", ACTIVITY, timedelta(hours=26), steps_today),
    ("sleep", ACTIVITY, DAILY_WINDOW, last_sleep),
    ("daily-resting-heart-rate", SERVICE, timedelta(days=3), resting_today),
)


INTERVAL = {"steps": "interval.start_time", "sleep": "interval.end_time"}
DAILY_TYPES = {"daily-resting-heart-rate"}
TYPE_NAME = re.compile(r"^[a-z][a-z-]{1,40}$")


def _rfc3339(at: datetime) -> str:
    return at.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def query(data_type: str, start: datetime, end: datetime) -> str:
    if not TYPE_NAME.match(data_type):
        raise ValueError("Tipo di dato Google Health non valido")
    name = data_type.replace("-", "_")
    if data_type in DAILY_TYPES:
        first, last = start.date().isoformat(), (end.date() + timedelta(days=1)).isoformat()
        return f'{name}.date >= "{first}" AND {name}.date < "{last}"'
    field = f"{name}.{INTERVAL.get(data_type, 'sample_time.physical_time')}"
    return f'{field} >= "{_rfc3339(start)}" AND {field} < "{_rfc3339(end)}"'


FATAL = {"api_disabled", "health_profile_missing", "scope_missing", "unauthorized", "health_grant", "health_preview", "not_linked"}


def _reason(exc: Exception) -> str:
    from agenti.google.errors import GoogleApiError
    if isinstance(exc, GoogleApiError):
        return exc.reason
    return "network" if isinstance(exc, httpx.HTTPError) else "error"


def ready(slug: str, service: str = SERVICE) -> bool:
    from agenti.google.gservices import google
    session = google.session(slug)
    return bool(session and session.ready(service))


def reset(slug: str, now: float | None = None) -> None:
    now = now or time.time()
    if slug in _state and now - _state[slug].get("at", 0.0) >= 10.0:
        _state[slug] = {**_state[slug], "at": 0.0}


def _keep(slug: str, samples: list[dict], now: float) -> int:
    added = 0
    for sample in samples:
        if live.put(slug, sample, "google_health", "cloud", now):
            history.record(slug, sample, "google_health", "cloud", now)
            added += 1
    return added


async def poll(slug: str, now: float | None = None) -> int:
    from agenti.google.gservices import google
    now = now or time.time()
    session = google.session(slug)
    if not session or not (session.ready(SERVICE) or session.ready(ACTIVITY)):
        _state[slug] = {"state": "unlinked", "at": now, "error": ""}
        return 0
    if now - _state.get(slug, {}).get("at", 0.0) < MIN_GAP:
        return 0
    lock = _locks.setdefault(slug, asyncio.Lock())
    if lock.locked():
        return 0
    async with lock:
        board.start(slug, "google_health", now)
        end = datetime.fromtimestamp(now, timezone.utc)
        added, error = 0, ""
        for data_type, key, field, metric, scale, window in SOURCES if session.ready(SERVICE) else ():
            try:
                body = await session._get(f"{BASE}/{data_type}/dataPoints", filter=query(data_type, end - window, end))
            except (httpx.HTTPError, ValueError) as exc:
                error = _reason(exc)
                log.info("Google Health %s non letto: %s", data_type, exc)
                if error in FATAL:
                    break
                continue
            added += _keep(slug, points(body, key, field, metric, now, scale), now)
        for data_type, service, window, parse in DAILY:
            if not session.ready(service):
                continue
            try:
                body = await session._get(f"{BASE}/{data_type}/dataPoints", filter=query(data_type, end - window, end))
            except (httpx.HTTPError, ValueError) as exc:
                error = error or _reason(exc)
                log.info("Google Health %s non letto: %s", data_type, exc)
                if _reason(exc) in FATAL:
                    break
                continue
            added += _keep(slug, parse(body, now), now)
        failed = bool(error and not added)
        _state[slug] = {"state": "error" if failed else "ok", "at": now, "error": error}
        if failed:
            board.fail(slug, "google_health", error, reason=error)
            journal.add(slug, "error", "cloud_error", {"reason": error}, now, quiet=600.0)
        else:
            board.ok(slug, "google_health")
            if added:
                journal.add(slug, "info", "cloud_ok", {}, now, quiet=1800.0)
    return added
