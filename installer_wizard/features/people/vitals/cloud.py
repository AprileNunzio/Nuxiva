import asyncio
import logging
import time
from datetime import datetime, timedelta, timezone

import httpx

from features.people.vitals.journal import journal
from features.people.vitals.live import live
from features.people.vitals.model import clean_sample

log = logging.getLogger("nuxiva.vitals.cloud")
BASE = "https://health.googleapis.com/v4/users/me/dataTypes"
SERVICE = "health"
WINDOW = timedelta(minutes=10)
MIN_GAP = 60.0
SOURCES = (
    ("heart-rate", "heartRate", "beatsPerMinute", "heart_rate"),
    ("oxygen-saturation", "oxygenSaturation", "percentage", "spo2"),
    ("core-body-temperature", "coreBodyTemperature", "temperatureCelsius", "body_temp"),
)
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


def points(body: dict, key: str, field: str, metric: str, now: float) -> list[dict]:
    out = []
    for item in (body.get("dataPoints") or []) if isinstance(body, dict) else []:
        inner = item.get(key) if isinstance(item, dict) else None
        if not isinstance(inner, dict):
            continue
        ts = parse_time(inner.get("sampleTime"))
        try:
            out.append(clean_sample({"metric": metric, "value": inner.get(field), "ts": ts if ts is not None else now}, now))
        except ValueError:
            continue
    return out


def ready(slug: str) -> bool:
    from features.google.gservices import google
    session = google.session(slug)
    return bool(session and session.ready(SERVICE))


async def poll(slug: str, now: float | None = None) -> int:
    from features.google.gservices import google
    now = now or time.time()
    session = google.session(slug)
    if not session or not session.ready(SERVICE):
        _state[slug] = {"state": "unlinked", "at": now, "error": ""}
        return 0
    if now - _state.get(slug, {}).get("at", 0.0) < MIN_GAP:
        return 0
    lock = _locks.setdefault(slug, asyncio.Lock())
    if lock.locked():
        return 0
    async with lock:
        end = datetime.fromtimestamp(now, timezone.utc)
        params = {"startTime": (end - WINDOW).strftime("%Y-%m-%dT%H:%M:%SZ"), "endTime": end.strftime("%Y-%m-%dT%H:%M:%SZ")}
        added, error = 0, ""
        for data_type, key, field, metric in SOURCES:
            try:
                body = await session._get(f"{BASE}/{data_type}/dataPoints", **params)
            except (httpx.HTTPError, ValueError) as exc:
                error = type(exc).__name__
                log.info("Google Health %s non letto: %s", data_type, exc)
                continue
            for sample in points(body, key, field, metric, now):
                added += live.put(slug, sample, "google_health", "cloud", now)
        failed = bool(error and not added)
        _state[slug] = {"state": "error" if failed else "ok", "at": now, "error": error}
        if failed:
            journal.add(slug, "error", "cloud_error", {"reason": error}, now, quiet=600.0)
        elif added:
            journal.add(slug, "info", "cloud_ok", {}, now, quiet=1800.0)
    return added
