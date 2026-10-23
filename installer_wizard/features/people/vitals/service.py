import secrets
import threading
import time
from collections import deque

from features.nodes.registry import registry
from features.people.vitals import cloud
from features.people.vitals.book import book
from features.people.vitals.lease import arbiter
from features.people.vitals.journal import journal
from features.people.vitals.live import live
from features.people.vitals.model import METRICS, clean_sample
from features.people.vitals.nearby import nearby

SEEN_SECONDS = 45.0
ERROR_CODES = {"connect_failed", "no_profiles", "disconnected", "scan_failed"}
_seen: dict[str, dict] = {}
_holders: dict[str, str] = {}
_drops: dict[str, tuple[str, float]] = {}
DROP_SECONDS = 40.0


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
pair_limit = RateLimit(10, 60.0)


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
    live.prune(now)
    return {"accepted": accepted, "rejected": rejected}


def _log_lease(slug: str, node: str, now: float) -> None:
    previous = _holders.get(slug, "")
    if previous != node:
        _holders[slug] = node
        journal.add(slug, "info", "lease_taken", {"node": node}, now)


def _node_feedback(node_id: str, report: dict, now: float) -> None:
    for row in [r for r in (report.get("errors") or [])[:20] if isinstance(r, dict)]:
        device = book.by_address(str(row.get("address", "")).upper())
        code = str(row.get("code", ""))
        if code == "scan_failed":
            for slug in {d["slug"] for d in book.all_devices() if d["kind"] == "ble"}:
                journal.add(slug, "error", code, {"node": node_id}, now, quiet=300.0)
        elif device and code in ERROR_CODES:
            journal.add(device["slug"], "warn" if code == "disconnected" else "error", code, {"device": device["label"], "node": node_id}, now, quiet=60.0)
    for address, metrics in (report.get("profiles") or {}).items() if isinstance(report.get("profiles"), dict) else []:
        device = book.by_address(str(address).upper())
        if not device or not isinstance(metrics, list):
            continue
        usable = sorted({str(m) for m in metrics[:8] if str(m) in METRICS})
        device["profiles"] = usable
        if usable:
            journal.add(device["slug"], "info", "connected", {"device": device["label"], "node": node_id, "metrics": ",".join(usable)}, now, quiet=120.0)
        else:
            journal.add(device["slug"], "error", "no_profiles", {"device": device["label"], "node": node_id}, now, quiet=300.0)


def node_report(node_id: str, report: dict, now: float | None = None) -> dict:
    now = now or time.time()
    faces = {str(s)[:64] for s in (report.get("faces") or [])[:16]}
    seen = [r for r in (report.get("seen") or [])[:40] if isinstance(r, dict)]
    claimed = set()
    for row in seen:
        device = book.by_address(str(row.get("address", "")).upper())
        if device and device["kind"] == "ble":
            holder = arbiter.claim(device["slug"], node_id, row.get("rssi"), device["slug"] in faces, now)
            _seen[device["address"]] = {"node": node_id, "at": now}
            claimed.add(device["slug"])
            if holder == node_id:
                _log_lease(device["slug"], node_id, now)
    for slug in faces - claimed:
        if any(d["kind"] == "ble" for d in book.of(slug)):
            if arbiter.claim(slug, node_id, -80, True, now) == node_id:
                _log_lease(slug, node_id, now)
    _node_feedback(node_id, report, now)
    nearby.report(node_id, report.get("nearby"), now)
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
        if result["accepted"]:
            journal.add(device["slug"], "info", "streaming", {"device": device["label"], "node": node_id}, now, quiet=600.0)
    connect = [d["address"] for d in (book.by_address(a) for a in book.addresses()) if d and arbiter.holder(d["slug"], now) == node_id]
    drop = [{"address": a, "nonce": n} for a, (n, t) in list(_drops.items()) if now - t <= DROP_SECONDS]
    return {"watch": book.addresses(), "connect": connect, "drop": drop, "discover": nearby.active(now), "accepted": accepted,
            "rejected": rejected, "ignored": ignored}


def drop_device(device: dict, now: float | None = None) -> None:
    now = now or time.time()
    address = device.get("address", "")
    if address:
        _drops[address] = (secrets.token_hex(4), now)
        _seen.pop(address, None)
    arbiter.release(device["slug"], arbiter.holder(device["slug"], now))
    live.forget(device["slug"])


def device_state(device: dict, values: dict, now: float) -> str:
    if not device.get("enabled", True):
        return "off"
    if any(str(v.get("source", "")).split("@")[0] == device["id"] for v in values.values()):
        return "streaming"
    if device["kind"] != "ble":
        return "waiting"
    if device.get("profiles") == [] and arbiter.holder(device["slug"], now):
        return "unsupported"
    held = arbiter.holder(device["slug"], now)
    if held and device.get("profiles"):
        return "connected"
    seen = _seen.get(device.get("address", ""))
    return "seen" if seen and now - seen["at"] <= SEEN_SECONDS else "waiting"


def devices_view(slug: str, values: dict, now: float) -> list[dict]:
    return [{**d, "state": device_state(book.raw(d["id"]) or d, values, now)} for d in book.of(slug)]


def capable_nodes(now: float | None = None) -> list[str]:
    now = now or time.time()
    return [n["name"] for n in registry.listing() if n.get("online") and "vitals_ble" in (n.get("capabilities") or [])]


def snapshot(slug: str, now: float | None = None) -> dict:
    now = now or time.time()
    return {"values": live.latest(slug, now), "lease": arbiter.view(slug, now),
            "cloud": {"ready": cloud.ready(slug), **cloud.status(slug)}}


def units() -> dict:
    return {k: v["unit"] for k, v in METRICS.items()}
