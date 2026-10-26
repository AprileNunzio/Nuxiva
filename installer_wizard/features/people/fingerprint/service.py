import hmac
import secrets
import threading
import time
from collections import deque

from features.nodes.registry import registry
from features.people import people
from features.people.fingerprint.model import EVENTS, FINGERS, clean_reader, clean_template
from features.people.fingerprint.readers import readers
from features.people.fingerprint.store import bindings
from state import store

ENROLL_TTL = 120.0
FAIL_LIMIT = 5
FAIL_WINDOW = 60.0
LOCK_SECONDS = 120.0
MAX_EVENTS = 8
RECENT_SECONDS = 600.0


class Service:
    def __init__(self) -> None:
        self._enroll: dict[str, dict] = {}
        self._fails: dict[str, deque] = {}
        self._locked: dict[str, float] = {}
        self._recent: dict[str, dict] = {}
        self._lock = threading.Lock()

    def start_enroll(self, slug: str, finger: str, reader_key: str, now: float | None = None) -> dict:
        now = now or time.time()
        if finger not in FINGERS:
            raise ValueError("Dito non valido")
        row = readers.get(reader_key, now)
        if not row:
            raise ValueError("Lettore non raggiungibile")
        token = secrets.token_urlsafe(12)
        with self._lock:
            self._enroll = {k: v for k, v in self._enroll.items() if v["expires"] > now and v["slug"] != slug}
            self._enroll[token] = {"slug": slug, "finger": finger, "reader": reader_key, "expires": now + ENROLL_TTL}
        return {"token": token, "expires_in": int(ENROLL_TTL), "reader": row}

    def cancel_enroll(self, slug: str) -> None:
        with self._lock:
            self._enroll = {k: v for k, v in self._enroll.items() if v["slug"] != slug}

    def pending(self, slug: str, now: float | None = None) -> dict | None:
        now = now or time.time()
        with self._lock:
            for value in self._enroll.values():
                if value["slug"] == slug and value["expires"] > now:
                    return {"finger": value["finger"], "reader": value["reader"], "expires_in": int(value["expires"] - now)}
        return None

    def _orders(self, node_id: str, now: float) -> list[dict]:
        with self._lock:
            return [{"token": t, "reader": v["reader"].split(":", 1)[1], "finger": v["finger"]}
                    for t, v in self._enroll.items() if v["expires"] > now and v["reader"].startswith(f"{node_id}:")]

    def _take(self, token: str, reader_key: str, now: float) -> dict | None:
        with self._lock:
            for known, value in list(self._enroll.items()):
                if hmac.compare_digest(known, token):
                    if value["expires"] <= now or value["reader"] != reader_key:
                        return None
                    del self._enroll[known]
                    return value
        return None

    def _blocked(self, reader_key: str, now: float) -> bool:
        return self._locked.get(reader_key, 0.0) > now

    def _fail(self, reader_key: str, now: float) -> None:
        window = self._fails.setdefault(reader_key, deque(maxlen=FAIL_LIMIT))
        window.append(now)
        if len(window) == FAIL_LIMIT and now - window[0] <= FAIL_WINDOW:
            self._locked[reader_key] = now + LOCK_SECONDS
            window.clear()
            store.event("WARN", f"Lettore impronte {reader_key} bloccato per troppi tentativi falliti", "fingerprint")

    def _matched(self, reader: dict, found: dict, now: float) -> dict | None:
        slug = found["slug"]
        profile = people.load(slug)
        if not profile or not bindings.enabled(slug):
            return None
        people.observe(slug, profile.get("name", slug), now)
        self._recent[slug] = {"room": reader["room"], "reader": reader["key"], "at": now}
        store.event("INFO", f"Impronta riconosciuta: {profile.get('name', slug)} in {reader['room'] or 'stanza non indicata'}", "fingerprint")
        return {"slug": slug, "name": profile.get("name", slug), "room": reader["room"]}

    def _event(self, reader: dict, event: dict, now: float) -> dict | None:
        kind = str(event.get("type", ""))
        if kind not in EVENTS:
            return None
        key = reader["key"]
        if kind == "match":
            if self._blocked(key, now):
                return {"type": "locked"}
            found = bindings.resolve(key, clean_template(event.get("template")))
            result = self._matched(reader, found, now) if found else None
            if not result:
                self._fail(key, now)
                return {"type": "denied"}
            return {"type": "matched", **result}
        if kind == "no_match":
            self._fail(key, now)
            return {"type": "denied"}
        order = self._take(str(event.get("enrollment", ""))[:64], key, now)
        if not order:
            return {"type": "enroll_rejected"}
        if kind == "enroll_failed":
            return {"type": "enroll_failed"}
        template = clean_template(event.get("template"))
        if not template:
            return {"type": "enroll_rejected"}
        bindings.bind(order["slug"], key, template, order["finger"], now)
        store.event("INFO", f"Impronta registrata per {order['slug']} ({order['finger']})", "fingerprint")
        return {"type": "enrolled", "slug": order["slug"], "finger": order["finger"]}

    def node_report(self, node_id: str, report: dict, now: float | None = None) -> dict:
        now = now or time.time()
        node = registry.data["nodes"].get(node_id) or {}
        results = []
        for row in [r for r in (report.get("readers") or [])[:8] if isinstance(r, dict)]:
            reader_id = clean_reader(row.get("reader"))
            if not reader_id:
                continue
            reader = readers.seen(node_id, node.get("room", ""), reader_id, row.get("transport"), row.get("label"), now)
            for event in [e for e in (row.get("events") or [])[:MAX_EVENTS] if isinstance(e, dict)]:
                outcome = self._event(reader, event, now)
                if outcome:
                    results.append({"reader": reader_id, **outcome})
        return {"enroll": self._orders(node_id, now), "results": results}

    def last_seen(self, slug: str, now: float | None = None) -> dict | None:
        now = now or time.time()
        row = self._recent.get(slug)
        return row if row and now - row["at"] <= RECENT_SECONDS else None

    def person_state(self, slug: str, now: float | None = None) -> dict:
        now = now or time.time()
        return {"enabled": bindings.enabled(slug), "fingers": bindings.fingers(slug), "readers": readers.listing(now),
                "pending": self.pending(slug, now), "last": self.last_seen(slug, now)}


service = Service()
