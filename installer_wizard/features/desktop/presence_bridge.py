import json
import logging
import os
import time

from features.desktop.audience import Policy, Tracker
from features.desktop.privacy import flag, privacy
from state import store

log = logging.getLogger("nuxiva.desktop.presence")
DISPLAY_ROLES = frozenset({"owner", "family"})
STALE_SECONDS = 5.0
VOICE_WINDOW = 15.0
ROLE_TTL = 30.0


class NativeTracker:

    def __init__(self, engine) -> None:
        self.engine = engine

    def step(self, signals: dict, now_ms: int) -> dict:
        return json.loads(self.engine.step(json.dumps(signals), now_ms))


def _native_class():
    if os.environ.get("NUXIVA_NATIVE", "auto").strip() == "0":
        return None
    try:
        import nuxiva_native
    except ImportError:
        return None
    return getattr(nuxiva_native, "RustPresenceTracker", None)


def gate_enabled() -> bool:
    return flag("NUXIVA_DISPLAY_PRESENCE_GATE", True)


def show_options() -> dict:
    return {"guest_public": flag("NUXIVA_DISPLAY_GUEST_PUBLIC", False),
            "trust_guests": flag("NUXIVA_DISPLAY_TRUST_GUESTS", False)}


def _require_liveness() -> bool:
    from features.vision import selection
    return selection.liveness_mode() != "off"


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

    def signals(self, now: float) -> dict:
        from features.authz.heard import heard
        from features.people.presence import monitor
        presence = store.presence or {}
        faces = [face_signal(p) for p in presence.get("people") or [] if isinstance(p, dict)]
        voices = [{"person": proof.slug, "authorized": self._role(proof.slug, now) in DISPLAY_ROLES,
                   "score": proof.score, "at_ms": int(proof.at * 1000)} for proof in heard.recent(VOICE_WINDOW, now)]
        return {"vision": _vision_state(presence, monitor.updated_at, now), "faces": faces, "voices": voices}

    def _engine(self, wanted: Policy, now_ms: int):
        if self.tracker is not None and self.policy == wanted:
            return self.tracker
        native = _native_class()
        self.tracker = NativeTracker(native(json.dumps(wanted.as_dict()), now_ms)) if native else Tracker(wanted, now_ms)
        self.policy = wanted
        return self.tracker

    def update(self) -> dict:
        now = self.clock()
        now_ms = int(now * 1000)
        if not gate_enabled():
            self.last = {"kind": "authorized", "members": [], "guests": 0, "since_ms": now_ms, "nucleus_only": False}
        else:
            self.last = self._engine(policy(), now_ms).step(self.signals(now), now_ms)
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
