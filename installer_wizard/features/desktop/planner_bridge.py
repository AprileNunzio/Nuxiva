import json
import logging
import threading
import time

from state import store

from features.desktop import audience_view
from features.desktop.privacy import flag
from features.desktop.surfaces import surfaces
import native_module

log = logging.getLogger("nuxiva.desktop.planner")
SIZES = frozenset({"s", "m", "l", "xl", "full"})
AUDIO = frozenset({"music", "karaoke", "tv_player", "audio_spectrum"})
VIDEO = frozenset({"tv_player", "cam_stream", "live_cam"})
FORCED_PREFIXES = ("recall:", "test:", "bind:")
CONVERSATION_SECONDS = 60.0
KINDS = frozenset({"empty", "guest_only", "authorized", "mixed", "uncertain"})


def _native():
    return native_module.feature("display_plan")


def enabled() -> bool:
    return flag("NUXIVA_DISPLAY_PLANNER", True)


def _number(value, default: float, lo: float, hi: float) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return default
    return min(hi, max(lo, result)) if result == result else default


def forced(item: dict) -> bool:
    return bool(item.get("essential") or item.get("sticky") or item.get("pos")
                or str(item.get("key") or "").startswith(FORCED_PREFIXES))


def candidate(item: dict, now: float) -> dict:
    wid = str(item.get("id") or "")
    size = "full" if item.get("takeover") or item.get("fullscreen") else str(item.get("size") or "m").lower()
    shown = _number(item.get("shown_at"), now, 0, now)
    expires = item.get("expires_at")
    ttl = int(max(0.0, _number(expires, now, 0, 1e12) - shown) * 1000) if expires else None
    return {"key": str(item.get("key") or wid), "widget": wid,
            "importance": int(_number(item.get("priority"), 50, 0, 100)), "urgency": 3 if item.get("urgent") else 0,
            "sensitivity": audience_view.sensitivity(item), "size": size if size in SIZES else "m",
            "cost": _number(item.get("weight"), 1.0, 0.0, 64.0), "forced": forced(item), "intent": bool(item.get("intent")),
            "guest_safe": bool(item.get("guest_safe")), "relevance": 1.0 if item.get("intent") else 0.0,
            "media": "audio" if wid in AUDIO else None, "exclusive": "video" if wid in VIDEO and size == "full" else None,
            "age_ms": int((now - shown) * 1000), "ttl_ms": ttl}


def context(audience: dict, members: list[dict], now: float) -> dict:
    kind = (audience or {}).get("kind")
    dialogue = getattr(store, "live_dialogue", None) or {}
    talking = now - _number(dialogue.get("ts") if isinstance(dialogue, dict) else 0, 0, 0, now) < CONVERSATION_SECONDS
    from features.agency.presence import intent as agency_intent
    project = bool(agency_intent.current())
    present = sorted({str(m.get("person")) for m in members if m.get("person")})
    from features.desktop.presence_bridge import bridge, show_options
    show = show_options()
    return {"audience": kind if kind in KINDS else "uncertain", "present": present,
            "alone": bridge.last.get("guests", 0) == 0 and len(present) <= 1,
            "mode": "conversation" if talking else ("project" if project else "ambient"),
            "guest_public": show["guest_public"], "trust_guests": show["trust_guests"]}


class PlannerBridge:

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.previous: dict[int, dict] = {}
        self.last: dict[int, dict] = {}

    def plans(self, items: list[dict], audience: dict, now: float) -> dict[int, dict] | None:
        engine = _native()
        if engine is None or not enabled():
            return None
        from features.desktop.learner_bridge import bridge as learner
        from features.desktop.presence_bridge import bridge
        ctx = context(audience, bridge.present(), now)
        screens = sorted({int(i.get("screen", 0)) for i in items if isinstance(i.get("screen"), int) and i["screen"] >= 0}) or [0]
        out = {}
        for screen in screens:
            mine = [candidate(i, now) for i in items if i.get("screen", 0) in (screen, -1)]
            learned = learner.preferences([c["widget"] for c in mine], screen, ctx["mode"], items, now)
            for c in mine:
                c["preference"] = learned.get(c["widget"], 0.0)
                c["interacted_ms"] = learner.interaction_ms(c["key"], now)
            previous = {"shown": {k: v for k, v in self.previous.get(screen, {}).items()}}
            here = {**ctx, "audience": surfaces.audience_for(screen, ctx["audience"])}
            payload = {"screen": {"id": screen}, "context": here, "candidates": mine, "previous": previous,
                       "now_ms": int(now * 1000)}
            out[screen] = json.loads(engine(json.dumps(payload)))
        return out

    def apply(self, snap: dict, audience: dict) -> dict:
        items = [i for i in snap.get("desk") or [] if isinstance(i, dict)]
        now = time.time()
        from features.desktop.learner_bridge import bridge as learner
        learner.observe_desk(items, now)
        try:
            plans = self.plans(items, audience, now)
        except ValueError as exc:
            log.error("Piano della scena non calcolato, uso la disposizione classica: %s", exc)
            return snap
        if plans is None:
            return snap
        placed = {}
        for screen, scene in plans.items():
            for s in scene.get("shown") or []:
                placed.setdefault(s["key"], s)
        desk = [{**i, "planned": True, "slot": placed[i["key"]].get("slot"), "muted": bool(placed[i["key"]].get("muted"))}
                for i in items if i.get("key") in placed]
        with self._lock:
            self.previous = {screen: {s["key"]: [s["slot"], s["since_ms"]] for s in scene.get("shown") or [] if s.get("slot")}
                             for screen, scene in plans.items()}
            self.last = plans
        scene = {str(screen): {"nucleus": p["nucleus"]["form"], "cap": p["cap"], "rows": p["rows"]} for screen, p in plans.items()}
        return {**snap, "desk": desk, "scene": scene}

    def explain(self) -> dict:
        with self._lock:
            return {"engine": "rust" if _native() else "classic", "enabled": enabled(),
                    "screens": {str(k): {"nucleus": v["nucleus"], "cap": v["cap"], "explain": v["explain"]}
                                for k, v in self.last.items()}}


bridge = PlannerBridge()
