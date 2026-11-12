import logging
import math
import os
import time
import uuid

from agenti.people import people
from state import store

log = logging.getLogger("nuxiva.people.details")
KEY = "face_traits"
SCORES = ("glasses", "beard", "fringe", "cigarette")
KINDS = ("glasses", "beard", "fringe", "hair_color", "smoking", "smoker")
MIN_SAMPLES = 4
MIN_GAP = 5.0
SAVE_EVERY = 60.0
PROFILE_TTL = 60.0
MAX_EVENTS = 200
MAX_PEOPLE = 64


def look_class():
    if os.environ.get("NUXIVA_NATIVE", "auto").strip() == "0":
        return None
    try:
        import nuxiva_native
    except ImportError:
        return None
    return getattr(nuxiva_native, "RustFaceLook", None)


def enabled() -> bool:
    from config import env_get
    return env_get("NUXIVA_LEARN_LOOK", "1").strip().lower() not in ("0", "off", "no", "false")


def clean(details) -> dict | None:
    if not isinstance(details, dict):
        return None
    try:
        raw = {k: float(details.get(k) or 0.0) for k in SCORES}
        count = int(details.get("samples") or 0)
    except (TypeError, ValueError, OverflowError):
        return None
    if not all(math.isfinite(v) for v in raw.values()) or count < MIN_SAMPLES:
        return None
    sample: dict = {k: max(0.0, min(1.0, v)) for k, v in raw.items()}
    sample["samples"] = min(count, 1000)
    hair = details.get("hair")
    sample["hair"] = hair if isinstance(hair, str) and len(hair) <= 16 and hair.isascii() and hair.isalpha() else None
    return sample


def _stored(profile: dict) -> dict:
    data = profile.get(KEY)
    if not isinstance(data, dict):
        return {"state": "", "events": []}
    events = [e for e in data.get("events") or [] if isinstance(e, dict)]
    return {"state": data.get("state") if isinstance(data.get("state"), str) else "", "events": events[:MAX_EVENTS]}


def _open(cls, state: str, slug: str):
    try:
        return cls(state or None)
    except ValueError as exc:
        log.warning("Memoria dell'aspetto di %s non leggibile, riparto da zero: %s", slug, exc)
        return cls(None)


class Mind:
    def __init__(self, memory, events: list, consent: bool, now: float) -> None:
        self.memory = memory
        self.events = events
        self.consent = consent
        self.checked = now
        self.saved = now
        self.dirty = False


class DetailLearner:
    def __init__(self) -> None:
        self.minds: dict[str, Mind] = {}
        self.seen: dict[str, tuple] = {}

    def _mind(self, cls, slug: str, now: float) -> Mind | None:
        mind = self.minds.get(slug)
        if mind is not None and now - mind.checked < PROFILE_TTL:
            return mind
        profile = people.load(slug)
        if profile is None:
            self.minds.pop(slug, None)
            return None
        consent = bool(profile.get("consent", True))
        if mind is not None:
            mind.consent, mind.checked = consent, now
            return mind
        stored = _stored(profile)
        memory = _open(cls, stored["state"], slug)
        if len(self.minds) >= MAX_PEOPLE:
            self._save_all(now, force=True)
            self.minds.clear()
        mind = self.minds[slug] = Mind(memory, stored["events"], consent, now)
        return mind

    def ingest(self, visible: list, now: float | None = None) -> list[dict]:
        cls = look_class()
        if cls is None or not enabled():
            return []
        now = now or time.time()
        learned = []
        for p in visible:
            slug = p.get("slug")
            if not p.get("known") or not slug or (p.get("liveness") or {}).get("state") == "spoof":
                continue
            sample = clean(p.get("details"))
            if sample is None:
                continue
            mark, last = p["details"].get("at"), self.seen.get(slug)
            if last and (last[0] == mark or now - last[1] < MIN_GAP):
                continue
            self.seen[slug] = (mark, now)
            mind = self._mind(cls, slug, now)
            if mind is None or not mind.consent:
                continue
            for event in mind.memory.update(sample, now):
                row = {"id": uuid.uuid4().hex[:10], "at": now, "status": "auto", **event}
                mind.events = [row, *mind.events][:MAX_EVENTS]
                learned.append({"slug": slug, **row})
                mind.dirty = True
                store.event("INFO", f"Appreso dall'aspetto di {slug}: {event['kind']} {event['value']}", "people")
            mind.dirty = True
        self._save_all(now, force=bool(learned))
        return learned

    def _save_all(self, now: float, force: bool = False) -> None:
        for slug, mind in list(self.minds.items()):
            if mind.dirty and (force or now - mind.saved >= SAVE_EVERY):
                self._save(slug, mind, now)

    def _save(self, slug: str, mind: Mind, now: float) -> None:
        with people._lock:
            profile = people.load(slug)
            if profile is None:
                self.minds.pop(slug, None)
                return
            profile[KEY] = {"state": mind.memory.state(), "events": mind.events}
            people.save(profile)
        mind.saved, mind.dirty = now, False

    def view(self, slug: str) -> dict:
        profile = people.load(slug)
        if profile is None:
            raise KeyError(slug)
        stored = _stored(profile)
        cls = look_class()
        summary = dict(_open(cls, stored["state"], slug).summary()) if cls is not None else None
        return {"available": cls is not None, "consent": bool(profile.get("consent", True)),
                "summary": summary, "events": stored["events"][:60]}

    def feedback(self, slug: str, entry_id: str, verdict: str) -> dict | None:
        if verdict not in ("ok", "wrong"):
            raise ValueError("giudizio non valido")
        cls = look_class()
        with people._lock:
            profile = people.load(slug)
            if profile is None:
                raise KeyError(slug)
            stored = _stored(profile)
            row = next((e for e in stored["events"] if e.get("id") == entry_id), None)
            if row is None:
                return None
            row["status"] = "confirmed" if verdict == "ok" else "rejected"
            if verdict == "wrong" and cls is not None and row.get("kind") in KINDS:
                memory = _open(cls, stored["state"], slug)
                memory.forget(row["kind"])
                stored["state"] = memory.state()
            profile[KEY] = stored
            people.save(profile)
        self.minds.pop(slug, None)
        return row

    def forget_person(self, slug: str) -> None:
        self.minds.pop(slug, None)
        self.seen.pop(slug, None)


learner = DetailLearner()
