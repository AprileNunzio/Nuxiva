import json
import logging
import os
import re
import threading
import time
from collections import OrderedDict
from pathlib import Path

from config import STATE_DIR
from features.stage import director

log = logging.getLogger("nuxiva.stage")

WEIGHTS_FILE = Path(os.environ.get("NUXIVA_STAGE_WEIGHTS", str(STATE_DIR / "stage_weights.json")))
CLIENT = re.compile(r"^[A-Za-z0-9_-]{1,40}$")
WIDGET = re.compile(r"^[a-z0-9_]{1,40}$")
MODES = ("face", "brain", "focus", "flow")
MAX_CLIENTS = 64
STEP = 8.0
DECAY = 0.9

BASE = (
    {"id": "chat", "priority": 60, "dwell_ms": 1200},
    {"id": "mic", "priority": 100, "group": "listening", "pinned": True},
    {"id": "rail_voice", "priority": 30, "group": "listening", "dwell_ms": 3000},
    {"id": "thinking", "priority": 55, "dwell_ms": 3000},
    {"id": "presence", "priority": 60, "dwell_ms": 3000},
    {"id": "rail_home", "priority": 60, "dwell_ms": 4000},
    {"id": "rail_scan", "priority": 62, "dwell_ms": 4000},
    {"id": "rail_vitals", "priority": 58, "dwell_ms": 4000},
    {"id": "rail_learned", "priority": 56, "dwell_ms": 4000},
    {"id": "project", "priority": 55, "group": "project", "dwell_ms": 4000},
    {"id": "music_clock", "priority": 55, "group": "music", "dwell_ms": 2000},
    {"id": "brain_badge", "priority": 58, "dwell_ms": 3000},
)
FLAGS = {"presence": "show_presence", "thinking": "show_thinking"}
WIDGET_GROUPS = {"listening": ("listening", 70), "project_status": ("project", 70), "music": ("music", 70)}
FEEDBACK_SURFACES = frozenset(s["id"] for s in BASE) | frozenset(f"w:{w}" for w in WIDGET_GROUPS)


def _bool(value) -> bool:
    return value is True


def clean_context(raw) -> dict:
    raw = raw if isinstance(raw, dict) else {}
    mode = raw.get("mode") if raw.get("mode") in MODES else "face"
    desk = raw.get("desk") if isinstance(raw.get("desk"), list) else []
    try:
        people = max(0, min(64, int(raw.get("people") or 0)))
    except (TypeError, ValueError):
        people = 0
    return {"mode": mode, "listening": _bool(raw.get("listening")), "conversing": _bool(raw.get("conversing")),
            "typing": _bool(raw.get("typing")), "speaking": _bool(raw.get("speaking")), "people": people,
            "desk": sorted({w for w in desk[:40] if isinstance(w, str) and WIDGET.match(w)}),
            "music": _bool(raw.get("music")), "project": _bool(raw.get("project"))}


class Stage:
    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.clients: OrderedDict[str, dict] = OrderedDict()
        self.weights: dict[str, dict[str, float]] | None = None

    def _weights(self) -> dict:
        if self.weights is None:
            try:
                data = json.loads(WEIGHTS_FILE.read_text(encoding="utf-8"))
                self.weights = {s: {k: float(v) for k, v in w.items() if isinstance(v, (int, float))}
                                for s, w in data.items() if s in FEEDBACK_SURFACES and isinstance(w, dict)}
            except (OSError, ValueError, AttributeError):
                self.weights = {}
        return self.weights

    def _save_weights(self) -> None:
        WEIGHTS_FILE.parent.mkdir(parents=True, exist_ok=True)
        tmp = WEIGHTS_FILE.with_suffix(".tmp")
        fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(self.weights, fh)
        os.replace(tmp, WEIGHTS_FILE)

    @staticmethod
    def surfaces(ctx: dict, settings: dict, intents: set[str]) -> list[dict]:
        own = settings.get("surfaces") if isinstance(settings.get("surfaces"), dict) else {}
        out = []
        for spec in BASE:
            sid = spec["id"]
            flag = FLAGS.get(sid)
            enabled = settings.get(flag) is not False if flag else own.get(sid, sid != "rail_voice") is not False
            out.append({**spec, "enabled": enabled})
        for wid in ctx["desk"]:
            if wid in WIDGET_GROUPS:
                group, priority = WIDGET_GROUPS[wid]
                out.append({"id": f"w:{wid}", "priority": priority, "group": group, "dwell_ms": 1000,
                            "pinned": wid in intents})
        return out

    def plan(self, client: str, raw_context, settings: dict, intents: set[str] | None = None) -> dict:
        if not CLIENT.match(client or ""):
            raise ValueError("client non valido")
        ctx = clean_context(raw_context)
        now = int(time.time() * 1000)
        with self.lock:
            prev = self.clients.get(client, {}).get("surfaces", {})
            req = {"now_ms": now, "context": ctx, "surfaces": self.surfaces(ctx, settings, intents or set()),
                   "previous": {k: {"state": v["state"], "since_ms": int(v["since_ms"])} for k, v in prev.items()
                                if v.get("state") in director.STATES},
                   "weights": self._weights()}
            result = director.plan(req)
            self.clients[client] = {**result, "at": now, "context": ctx}
            self.clients.move_to_end(client)
            while len(self.clients) > MAX_CLIENTS:
                self.clients.popitem(last=False)
        return {**result, "engine": director.native.ENGINE}

    def feedback(self, client: str, surface: str, wanted: bool) -> float:
        if surface not in FEEDBACK_SURFACES:
            raise ValueError("superficie sconosciuta")
        with self.lock:
            last = self.clients.get(client)
            if not last:
                raise KeyError(client)
            key = last["context_key"]
            weights = self._weights().setdefault(surface, {})
            value = weights.get(key, 0.0) * DECAY + (STEP if wanted else -STEP)
            weights[key] = round(max(-director.WEIGHT_LIMIT, min(director.WEIGHT_LIMIT, value)), 3)
            try:
                self._save_weights()
            except OSError as exc:
                log.warning("Preferenze del regista non salvate: %s", exc)
            return weights[key]

    def active(self) -> dict:
        with self.lock:
            return {c: {"context_key": v["context_key"], "at": v["at"],
                        "shown": sorted(k for k, s in v["surfaces"].items() if s["state"] == "shown"),
                        "min": sorted(k for k, s in v["surfaces"].items() if s["state"] == "min"),
                        "hidden": sorted(k for k, s in v["surfaces"].items() if s["state"] == "hidden")}
                    for c, v in self.clients.items()}


stage = Stage()
