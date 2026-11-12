import json
import logging
import time

from features.desktop.audience import Policy, Tracker
from features.desktop.privacy import flag, privacy
from state import store
import native_module

log = logging.getLogger("nuxiva.desktop.presence")
DISPLAY_ROLES = frozenset({"owner", "family"})
STALE_SECONDS = 15.0
VOICE_WINDOW = 60.0
GREETING_WINDOW = 60.0
ROLE_TTL = 30.0


class NativeTracker:

    def __init__(self, engine) -> None:
        self.engine = engine

    def step(self, signals: dict, now_ms: int) -> dict:
        return json.loads(self.engine.step(json.dumps(signals), now_ms))


def _native_class():
    return native_module.feature("RustPresenceTracker")


def gate_enabled() -> bool:
    return flag("NUXIVA_DISPLAY_PRESENCE_GATE", True)


def show_options() -> dict:
    return {"guest_public": flag("NUXIVA_DISPLAY_GUEST_PUBLIC", False),
            "trust_guests": flag("NUXIVA_DISPLAY_TRUST_GUESTS", False)}


def _require_liveness() -> bool:
    from features.vision import selection
    return selection.liveness_mode() == "strict"


def policy() -> Policy:
    return Policy(away_ms=int(privacy.away_seconds() * 1000), voice_hold_ms=int(privacy.voice_seconds() * 1000),
                  require_liveness=_require_liveness())


def _vision_state(presence: dict, updated_at: float, now: float) -> str:
    status = presence.get("status")
    if status == "disabled":
        return "disabled"
    if status != "ok" or now - updated_at > STALE_SECONDS:
        return "offline"
    return "ok"


def _liveness(raw) -> str:
    state = raw.get("state") if isinstance(raw, dict) else raw
    return state if state in ("live", "spoof") else "unknown"


def face_signal(person: dict) -> dict:
    slug = str(person.get("slug") or "") if person.get("known") else ""
    return {"person": slug or None, "authorized": bool(slug) and person.get("role") in DISPLAY_ROLES,
            "confidence": float(person.get("confidence") or 0.0), "liveness": _liveness(person.get("liveness")),
            "near": bool(person.get("near"))}


class PresenceBridge:

    def __init__(self, clock=time.time) -> None:
        self.clock = clock
        self.tracker = None
        self.policy: Policy | None = None
        self.roles: dict[str, tuple[str, float]] = {}
        self.last: dict = {"kind": "uncertain", "members": [], "guests": 0, "since_ms": 0, "nucleus_only": True}

    def _role(self, slug: str, now: float) -> str:
        cached = self.roles.get(slug)
        if cached and now - cached[1] < ROLE_TTL:
            return cached[0]
        from features.people import people
        role = str((people.load(slug) or {}).get("role") or "guest")
        self.roles[slug] = (role, now)
        return role

    def _person_signal(self, person: dict, strict: bool, now: float) -> dict:
        enriched = dict(person)
        if enriched.get("known") and enriched.get("slug") and not enriched.get("role"):
            enriched["role"] = self._role(str(enriched["slug"]), now)
        sig = face_signal(enriched)
        if not strict and sig["authorized"] and sig["liveness"] == "spoof":
            sig["liveness"] = "unknown"
        return sig

    def _corroborated_voices(self, people_list: list, now: float) -> list[dict]:
        from features.authz.heard import heard
        voices = [{"person": proof.slug, "authorized": self._role(proof.slug, now) in DISPLAY_ROLES,
                   "score": proof.score, "at_ms": int(proof.at * 1000)} for proof in heard.recent(VOICE_WINDOW, now)]
        greeting = getattr(store, "greeting", None)
        if isinstance(greeting, dict):
            gat = float(greeting.get("at") or 0.0)
            if 0.0 <= now - gat <= GREETING_WINDOW:
                names = set(greeting.get("names") or [])
                slugs = {str(greeting["slug"])} if greeting.get("slug") else set()
                for p in people_list:
                    if isinstance(p, dict) and p.get("known") and p.get("slug") and p.get("name") in names:
                        slugs.add(str(p["slug"]))
                for slug in slugs:
                    voices.append({"person": slug, "authorized": self._role(slug, now) in DISPLAY_ROLES,
                                   "score": 0.95, "at_ms": int(gat * 1000)})
        dlg = getattr(store, "live_dialogue", None)
        if isinstance(dlg, dict):
            dat = float(dlg.get("ts") or 0.0)
            dslug = str(dlg.get("speaker_slug") or "")
            if dslug and 0.0 <= now - dat <= VOICE_WINDOW:
                voices.append({"person": dslug, "authorized": self._role(dslug, now) in DISPLAY_ROLES,
                               "score": 0.9, "at_ms": int(dat * 1000)})
        return voices

    def signals(self, now: float) -> dict:
        from features.people.presence import monitor
        presence = store.presence or {}
        people_list = [p for p in presence.get("people") or [] if isinstance(p, dict)]
        strict = _require_liveness()
        faces = [self._person_signal(p, strict, now) for p in people_list]
        voices = self._corroborated_voices(people_list, now)
        vision = _vision_state(presence, monitor.updated_at, now)
        if vision == "offline" and presence.get("status") != "disabled" and any(v.get("authorized") for v in voices):
            vision = "ok"
        return {"vision": vision, "faces": faces, "voices": voices}

    def _native(self, wanted: Policy, now_ms: int) -> NativeTracker | None:
        native = _native_class()
        if native is None:
            return None
        try:
            return NativeTracker(native(json.dumps(wanted.as_dict()), now_ms))
        except ValueError as exc:
            log.warning("Motore nativo della presenza non compatibile, uso il motore Python: %s", exc)
            return None

    def _engine(self, wanted: Policy, now_ms: int):
        if self.tracker is not None and self.policy == wanted:
            return self.tracker
        self.tracker = self._native(wanted, now_ms) or Tracker(wanted, now_ms)
        self.policy = wanted
        return self.tracker

    def _step(self, wanted: Policy, now: float, now_ms: int) -> dict:
        engine = self._engine(wanted, now_ms)
        signals = self.signals(now)
        if not isinstance(engine, NativeTracker):
            return engine.step(signals, now_ms)
        try:
            return engine.step(signals, now_ms)
        except ValueError as exc:
            log.warning("Motore nativo della presenza non compatibile, uso il motore Python: %s", exc)
            self.tracker = Tracker(wanted, now_ms)
            return self.tracker.step(signals, now_ms)

    def update(self) -> dict:
        now = self.clock()
        now_ms = int(now * 1000)
        if not gate_enabled():
            self.last = {"kind": "authorized", "members": [], "guests": 0, "since_ms": now_ms, "nucleus_only": False}
        else:
            self.last = self._step(policy(), now, now_ms)
        self.publish()
        from features.sentinel.collectors.presence import collector
        collector.update(self.last, (store.presence or {}).get("people") or [], now)
        return self.last

    def view(self) -> dict:
        return {"kind": self.last["kind"], "nucleus_only": bool(self.last["nucleus_only"]),
                "since": round(self.last["since_ms"] / 1000, 3), "gate": gate_enabled()}

    def publish(self) -> None:
        public = self.view()
        before = store.audience or {}
        store.audience = public
        if (before.get("kind"), before.get("gate")) != (public["kind"], public["gate"]):
            log.info("Pubblico del display: %s", public["kind"])
            store.touch()

    def present(self) -> list[dict]:
        return [dict(m) for m in self.last["members"]]


bridge = PresenceBridge()
