import json
import re
import threading
import time

from agenti.agent import registry
from agenti.hands import events as hand_events

SHAPES = ("dispersed", "sphere", "torus", "cube", "helix")
GESTURES = (
    "idle",
    "open_palm_disperse",
    "single_hand_focus_morph",
    "wrist_rotation_tilt",
    "two_hand_pinch_stretch",
)
REAL_WORLD_PREFIXES = (
    "ha.",
    "home.",
    "system.",
    "device.",
    "light.",
    "lock.",
    "scene.run",
    "power.",
)
ACTION_RE = re.compile(r"^[a-z0-9_.:-]{1,64}$")
_lock = threading.Lock()
_state = {
    "enabled": False,
    "camera_active": False,
    "local_only": True,
    "person_present": False,
    "auto_close_timeout_s": 4,
    "shape": "sphere",
    "active_gesture": "idle",
    "hands_count": 0,
    "confidence": 0.0,
    "transform": {"yaw": 0.0, "pitch": 0.0, "roll": 0.0, "tx": 0.0, "ty": 0.0, "scale": 1.0},
    "bindings": {},
    "updated_at": 0.0,
}


def is_real_world_action(action: str) -> bool:
    clean = str(action or "").strip().lower()
    return any(clean.startswith(prefix) for prefix in REAL_WORLD_PREFIXES)


def _needs_confirm_binding(args: dict) -> bool:
    return is_real_world_action(str((args or {}).get("action", "")))


def snapshot() -> dict:
    with _lock:
        return {
            "enabled": _state["enabled"],
            "camera_active": _state["camera_active"],
            "local_only": True,
            "person_present": _state["person_present"],
            "auto_close_timeout_s": _state["auto_close_timeout_s"],
            "shape": _state["shape"],
            "active_gesture": _state["active_gesture"],
            "hands_count": _state["hands_count"],
            "confidence": _state["confidence"],
            "transform": dict(_state["transform"]),
            "bindings": dict(_state["bindings"]),
            "recent_intents": hand_events.recent()[-10:],
            "updated_at": _state["updated_at"],
        }


def update_from_display(payload: dict) -> dict:
    if not isinstance(payload, dict):
        return snapshot()
    with _lock:
        if "camera_active" in payload:
            _state["camera_active"] = bool(payload["camera_active"])
            _state["enabled"] = bool(payload["camera_active"])
        if "person_present" in payload:
            _state["person_present"] = bool(payload["person_present"])
        shape = str(payload.get("shape", "")).strip().lower()
        if shape in SHAPES:
            _state["shape"] = shape
        gesture = str(payload.get("active_gesture", "")).strip().lower()
        if gesture in GESTURES:
            _state["active_gesture"] = gesture
        if "hands_count" in payload:
            try:
                _state["hands_count"] = max(0, min(2, int(payload["hands_count"])))
            except (TypeError, ValueError):
                pass
        if "confidence" in payload:
            try:
                _state["confidence"] = round(max(0.0, min(1.0, float(payload["confidence"]))), 4)
            except (TypeError, ValueError):
                pass
        _state["updated_at"] = round(time.time(), 3)
    return snapshot()


@registry.tool(
    "spatial_hud_status",
    "Legge lo stato corrente dello Spatial Gesture HUD 3D (forma attiva, gesto, privacy camera, intenti semantici)",
    {},
    agent="hands",
)
async def spatial_hud_status() -> str:
    return json.dumps(snapshot(), ensure_ascii=False)


@registry.tool(
    "spatial_hud_set_mode",
    "Attiva o disattiva lo Spatial Gesture HUD sul display principale con policy privacy locale e auto-chiusura",
    {
        "enabled": "true per attivare la sessione olografica locale, false per spegnere la telecamera e resettare",
        "auto_close_s": "secondi prima dello spegnimento automatico quando la persona esce dall'inquadratura (1-60)",
    },
    agent="hands",
)
async def spatial_hud_set_mode(enabled: bool = True, auto_close_s: int = 4) -> str:
    timeout = max(1, min(60, int(auto_close_s)))
    with _lock:
        _state["enabled"] = bool(enabled)
        _state["camera_active"] = bool(enabled)
        _state["auto_close_timeout_s"] = timeout
        if not enabled:
            _state["person_present"] = False
            _state["active_gesture"] = "idle"
            _state["hands_count"] = 0
            _state["confidence"] = 0.0
        _state["updated_at"] = round(time.time(), 3)
    hand_events.record([{"type": "gesture", "gesture": "spatial_hud.mode", "action": "on" if enabled else "off"}])
    return json.dumps(snapshot(), ensure_ascii=False)


@registry.tool(
    "spatial_hud_set_shape",
    "Imposta la geometria olografica 3D dello Spatial Gesture HUD (dispersed, sphere, torus, cube, helix)",
    {"shape": "geometria 3D: dispersed, sphere, torus, cube oppure helix"},
    agent="hands",
)
async def spatial_hud_set_shape(shape: str = "sphere") -> str:
    clean = str(shape or "").strip().lower()
    aliases = {"ring": "torus", "spiral": "helix"}
    clean = aliases.get(clean, clean)
    if clean not in SHAPES:
        raise ValueError(f"forma non valida «{shape}»: usa {', '.join(SHAPES)}")
    with _lock:
        _state["shape"] = clean
        _state["updated_at"] = round(time.time(), 3)
    hand_events.record([{"type": "gesture", "gesture": "spatial_hud.shape", "action": clean}])
    return json.dumps(snapshot(), ensure_ascii=False)


@registry.tool(
    "spatial_hud_bind_gesture_action",
    "Associa un gesto spaziale 3D a un'azione (richiede conferma Zero-Trust per azioni su dispositivi o sistema)",
    {
        "gesture": "gesto spaziale: open_palm_disperse, single_hand_focus_morph, wrist_rotation_tilt, two_hand_pinch_stretch",
        "action": "identificatore azione (es. view.rotate, home.light.toggle, system.lock)",
    },
    confirm=_needs_confirm_binding,
    agent="hands",
)
async def spatial_hud_bind_gesture_action(gesture: str, action: str) -> str:
    clean_gesture = str(gesture or "").strip().lower()
    clean_action = str(action or "").strip()
    if clean_gesture not in GESTURES or clean_gesture == "idle":
        raise ValueError(f"gesto non valido «{gesture}»")
    if not ACTION_RE.match(clean_action):
        raise ValueError(f"azione non valida «{action}»")
    requires_confirm = is_real_world_action(clean_action)
    entry = {
        "gesture": clean_gesture,
        "action": clean_action,
        "requires_confirmation": requires_confirm,
    }
    with _lock:
        _state["bindings"][clean_gesture] = entry
        _state["updated_at"] = round(time.time(), 3)
    hand_events.record([{"type": "action", "gesture": clean_gesture, "action": clean_action}])
    return json.dumps(entry, ensure_ascii=False)
