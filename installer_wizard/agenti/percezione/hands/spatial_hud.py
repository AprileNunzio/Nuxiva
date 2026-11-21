import json
import re
import threading
import time

from agenti.agent import registry
from agenti.hands import events as hand_events

SHAPES = ("dispersed", "sphere", "torus", "cube", "helix", "procedural")
FIDELITIES = ("particles", "mesh_3d", "photoreal_pbr")
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
    "subject": "",
    "fidelity": "particles",
    "csg_nodes": [],
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


def _normalize_fidelity(raw: str) -> str:
    clean = str(raw or "").strip().lower()
    aliases = {
        "particle": "particles",
        "ologramma": "particles",
        "hologram": "particles",
        "3d": "mesh_3d",
        "mesh": "mesh_3d",
        "solid": "mesh_3d",
        "realistic": "photoreal_pbr",
        "realistica": "photoreal_pbr",
        "realistico": "photoreal_pbr",
        "pbr": "photoreal_pbr",
        "gta6": "photoreal_pbr",
    }
    mapped = aliases.get(clean, clean)
    return mapped if mapped in FIDELITIES else "particles"


def _procedural_csg_nodes(subject: str) -> list[dict]:
    low = subject.strip().lower()
    if any(k in low for k in ("macchina", "auto", "car", "supercar", "veicol", "ferrari", "lamborghini")):
        return [
            {"name": "chassis", "shape": "box", "size": [1.92, 0.36, 4.35], "position": [0.0, -0.12, 0.0], "color": "#e11d48", "metal": 0.88, "roughness": 0.14, "clearcoat": 0.96, "emissive": 0.0},
            {"name": "hood", "shape": "wedge", "size": [1.86, 0.32, 1.45], "position": [0.0, 0.08, 1.35], "color": "#e11d48", "metal": 0.88, "roughness": 0.14, "clearcoat": 0.96, "emissive": 0.0},
            {"name": "cabin", "shape": "capsule", "size": [1.52, 0.48, 1.95], "position": [0.0, 0.24, -0.15], "color": "#0f172a", "metal": 0.18, "roughness": 0.05, "clearcoat": 1.0, "emissive": 0.0},
            {"name": "rear_deck", "shape": "box", "size": [1.90, 0.34, 1.25], "position": [0.0, 0.08, -1.42], "color": "#e11d48", "metal": 0.88, "roughness": 0.14, "clearcoat": 0.96, "emissive": 0.0},
            {"name": "spoiler", "shape": "box", "size": [1.84, 0.06, 0.32], "position": [0.0, 0.38, -1.96], "color": "#1e293b", "metal": 0.5, "roughness": 0.3, "clearcoat": 0.4, "emissive": 0.0},
            {"name": "wheel_fl", "shape": "cylinder", "size": [0.36, 0.26, 0.36], "position": [-0.96, -0.24, 1.32], "color": "#111827", "metal": 0.1, "roughness": 0.82, "clearcoat": 0.0, "emissive": 0.0},
            {"name": "wheel_fr", "shape": "cylinder", "size": [0.36, 0.26, 0.36], "position": [0.96, -0.24, 1.32], "color": "#111827", "metal": 0.1, "roughness": 0.82, "clearcoat": 0.0, "emissive": 0.0},
            {"name": "wheel_rl", "shape": "cylinder", "size": [0.38, 0.28, 0.38], "position": [-0.98, -0.22, -1.32], "color": "#111827", "metal": 0.1, "roughness": 0.82, "clearcoat": 0.0, "emissive": 0.0},
            {"name": "wheel_rr", "shape": "cylinder", "size": [0.38, 0.28, 0.38], "position": [0.98, -0.22, -1.32], "color": "#111827", "metal": 0.1, "roughness": 0.82, "clearcoat": 0.0, "emissive": 0.0},
            {"name": "headlight_l", "shape": "box", "size": [0.36, 0.08, 0.12], "position": [-0.68, 0.02, 2.14], "color": "#e0f2fe", "metal": 0.1, "roughness": 0.1, "clearcoat": 0.6, "emissive": 2.8},
            {"name": "headlight_r", "shape": "box", "size": [0.36, 0.08, 0.12], "position": [0.68, 0.02, 2.14], "color": "#e0f2fe", "metal": 0.1, "roughness": 0.1, "clearcoat": 0.6, "emissive": 2.8},
            {"name": "taillight", "shape": "box", "size": [1.68, 0.07, 0.10], "position": [0.0, 0.12, -2.14], "color": "#ff1e42", "metal": 0.1, "roughness": 0.1, "clearcoat": 0.6, "emissive": 2.5},
        ]
    if any(k in low for k in ("aereo", "jet", "drone", "astronave", "razzo")):
        return [
            {"name": "fuselage", "shape": "capsule", "size": [0.65, 0.55, 3.6], "position": [0.0, 0.0, 0.0], "color": "#94a3b8", "metal": 0.92, "roughness": 0.18, "clearcoat": 0.85, "emissive": 0.0},
            {"name": "wings", "shape": "box", "size": [3.8, 0.09, 0.95], "position": [0.0, 0.0, -0.2], "color": "#cbd5e1", "metal": 0.9, "roughness": 0.2, "clearcoat": 0.8, "emissive": 0.0},
            {"name": "tail", "shape": "wedge", "size": [0.12, 0.75, 0.85], "position": [0.0, 0.42, -1.35], "color": "#64748b", "metal": 0.88, "roughness": 0.22, "clearcoat": 0.75, "emissive": 0.0},
            {"name": "thruster", "shape": "cylinder", "size": [0.35, 0.35, 0.35], "position": [0.0, 0.0, -1.85], "color": "#38bdf8", "metal": 0.2, "roughness": 0.1, "clearcoat": 0.5, "emissive": 2.6},
        ]
    seed = sum((i + 1) * ord(ch) for i, ch in enumerate(low or "nuxiva"))
    c1 = f"#{(40 + seed % 190):02x}{(80 + (seed * 3) % 160):02x}{(140 + (seed * 7) % 110):02x}"
    return [
        {"name": "core", "shape": "sphere", "size": [1.15, 1.15, 1.15], "position": [0.0, 0.0, 0.0], "color": c1, "metal": 0.86, "roughness": 0.15, "clearcoat": 0.94, "emissive": 0.25},
        {"name": "ring_outer", "shape": "torus", "size": [1.65, 0.16, 1.65], "position": [0.0, 0.0, 0.0], "color": "#38bdf8", "metal": 0.92, "roughness": 0.12, "clearcoat": 0.96, "emissive": 0.85},
        {"name": "pedestal", "shape": "cylinder", "size": [1.1, 0.25, 1.1], "position": [0.0, -0.95, 0.0], "color": "#1e293b", "metal": 0.75, "roughness": 0.25, "clearcoat": 0.6, "emissive": 0.0},
    ]


def snapshot() -> dict:
    with _lock:
        return {
            "enabled": _state["enabled"],
            "camera_active": _state["camera_active"],
            "local_only": True,
            "person_present": _state["person_present"],
            "auto_close_timeout_s": _state["auto_close_timeout_s"],
            "shape": _state["shape"],
            "subject": _state["subject"],
            "fidelity": _state["fidelity"],
            "csg_nodes": list(_state["csg_nodes"]),
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
        if "fidelity" in payload:
            _state["fidelity"] = _normalize_fidelity(str(payload["fidelity"]))
        if "subject" in payload and isinstance(payload["subject"], str):
            _state["subject"] = payload["subject"].strip()[:64]
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
    "Legge lo stato corrente dello Spatial Gesture HUD 3D (forma attiva, soggetto generato, fedeltà PBR, gesto, privacy camera)",
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
    "Imposta la geometria olografica 3D dello Spatial Gesture HUD (dispersed, sphere, torus, cube, helix, procedural)",
    {"shape": "geometria 3D: dispersed, sphere, torus, cube, helix oppure procedural"},
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
    "spatial_hud_generate_object",
    "Genera in tempo reale qualsiasi oggetto 3D richiesto (es. macchina, jet, edificio) e imposta il livello di rendering (particles, mesh_3d, photoreal_pbr stile GTA 6)",
    {
        "subject": "descrizione di qualsiasi oggetto da sintetizzare in 3D (es. macchina sportiva, drone, cuore, città)",
        "fidelity": "livello di rendering: particles (ologramma particellare), mesh_3d (solido 3D), photoreal_pbr (realistico PBR con clearcoat, riflessi e bloom)",
    },
    agent="hands",
)
async def spatial_hud_generate_object(subject: str, fidelity: str = "particles") -> str:
    clean_subj = str(subject or "").strip()[:64]
    if not clean_subj:
        raise ValueError("specifica il soggetto 3D da generare")
    tier = _normalize_fidelity(fidelity)
    nodes = _procedural_csg_nodes(clean_subj)
    try:
        from agenti.models3d import generator
        _, ai_parts, _ = await generator.design(clean_subj)
        if ai_parts:
            nodes = [
                {
                    "name": str(p.get("name", "part"))[:32],
                    "shape": str(p.get("shape", "box")),
                    "size": list(p.get("size") or [1.0, 1.0, 1.0])[:3],
                    "position": list(p.get("position") or [0.0, 0.0, 0.0])[:3],
                    "color": str(p.get("color") or "#38bdf8"),
                    "metal": 0.9 if p.get("metal") else 0.35,
                    "roughness": 0.14 if p.get("metal") else 0.4,
                    "clearcoat": 0.95 if tier == "photoreal_pbr" else 0.3,
                    "emissive": 0.0,
                }
                for p in ai_parts[:40]
            ]
    except Exception:
        pass
    with _lock:
        _state["enabled"] = True
        _state["shape"] = "procedural"
        _state["subject"] = clean_subj
        _state["fidelity"] = tier
        _state["csg_nodes"] = nodes
        _state["updated_at"] = round(time.time(), 3)
    hand_events.record([{"type": "gesture", "gesture": "spatial_hud.generate", "action": tier}])
    return json.dumps(snapshot(), ensure_ascii=False)


@registry.tool(
    "spatial_hud_set_fidelity",
    "Evolve il rendering dell'oggetto 3D corrente tra particelle olografiche (particles), solido 3D (mesh_3d) e fotorealismo PBR con sfumature, clearcoat e luci (photoreal_pbr)",
    {"fidelity": "particles, mesh_3d oppure photoreal_pbr"},
    agent="hands",
)
async def spatial_hud_set_fidelity(fidelity: str = "photoreal_pbr") -> str:
    tier = _normalize_fidelity(fidelity)
    with _lock:
        _state["fidelity"] = tier
        if _state["subject"] and not _state["csg_nodes"]:
            _state["csg_nodes"] = _procedural_csg_nodes(_state["subject"])
            _state["shape"] = "procedural"
        _state["updated_at"] = round(time.time(), 3)
    hand_events.record([{"type": "gesture", "gesture": "spatial_hud.fidelity", "action": tier}])
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
