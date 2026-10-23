import threading
import time
from collections import deque

from features.people.vitals import cloud
from features.people.vitals.book import book
from features.people.vitals.lease import arbiter
from features.people.vitals.live import live
from features.people.vitals.model import METRICS, clean_sample


class RateLimit:
    def __init__(self, limit: int, window: float) -> None:
        self.limit = limit
        self.window = window
        self._hits: dict[str, deque] = {}
        self._lock = threading.Lock()

    def allow(self, key: str, now: float | None = None) -> bool:
        now = now or time.time()
        with self._lock:
            hits = self._hits.setdefault(key, deque())
            while hits and now - hits[0] > self.window:
                hits.popleft()
            if len(hits) >= self.limit:
                return False
            hits.append(now)
            if len(self._hits) > 512:
                for stale in [k for k, h in self._hits.items() if not h or now - h[-1] > self.window]:
                    del self._hits[stale]
            return True


push_limit = RateLimit(120, 60.0)
node_limit = RateLimit(240, 60.0)


def ingest(slug: str, samples, source: str, kind: str, now: float | None = None) -> dict:
    now = now or time.time()
    accepted = rejected = 0
    for raw in samples:
        try:
            sample = clean_sample(raw, now)
        except ValueError:
            rejected += 1
            continue
        if live.put(slug, sample, source, kind, now):
            accepted += 1
    return {"accepted": accepted, "rejected": rejected}


def node_report(node_id: str, report: dict, now: float | None = None) -> dict:
    now = now or time.time()
    faces = {str(s)[:64] for s in (report.get("faces") or [])[:16]}
    seen = [r for r in (report.get("seen") or [])[:40] if isinstance(r, dict)]
    claimed = set()
    for row in seen:
        device = book.by_address(str(row.get("address", "")).upper())
        if device and device["kind"] == "ble":
            arbiter.claim(device["slug"], node_id, row.get("rssi"), device["slug"] in faces, now)
            claimed.add(device["slug"])
    for slug in faces - claimed:
        if any(d["kind"] == "ble" for d in book.of(slug)):
            arbiter.claim(slug, node_id, -80, True, now)
    accepted = rejected = ignored = 0
    for row in [r for r in (report.get("samples") or [])[:200] if isinstance(r, dict)]:
        device = book.by_address(str(row.get("address", "")).upper())
        if not device or device["kind"] != "ble" or arbiter.holder(device["slug"], now) != node_id:
            ignored += 1
            continue
        result = ingest(device["slug"], [row], f"{device['id']}@{node_id}", "ble", now)
        accepted += result["accepted"]
        rejected += result["rejected"]
        book.touch(device, now)
    connect = [d["address"] for d in (book.by_address(a) for a in book.addresses()) if d and arbiter.holder(d["slug"], now) == node_id]
    return {"watch": book.addresses(), "connect": connect, "accepted": accepted, "rejected": rejected, "ignored": ignored}


def snapshot(slug: str, now: float | None = None) -> dict:
    now = now or time.time()
    return {"values": live.latest(slug, now), "lease": arbiter.view(slug, now),
            "cloud": {"ready": cloud.ready(slug), **cloud.status(slug)}}


def units() -> dict:
    return {k: v["unit"] for k, v in METRICS.items()}
