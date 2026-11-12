import json
import os
import re

from config import STATE_DIR

NVR_DIR = STATE_DIR / "nvr"
SETTINGS_FILE = NVR_DIR / "settings.json"
LABELS = ("person", "car", "truck", "motorcycle", "bicycle", "dog", "cat", "bird", "package", "license_plate", "face", "motion")
HOST_RE = re.compile(r"^(?=.{1,253}$)[A-Za-z0-9]([A-Za-z0-9.-]{0,251}[A-Za-z0-9])?$")
TOPIC_RE = re.compile(r"^[A-Za-z0-9_/+#-]{1,120}$")
SECRET = "mqtt_password"
DEFAULTS = {"enabled": False, "mqtt_host": "", "mqtt_port": 1883, "mqtt_topic": "nvr/events", "mqtt_user": "", SECRET: "",
            "mqtt_tls": False, "retention_days": 30, "min_score": 0.6, "labels": list(LABELS[:4]) + ["dog", "cat", "package"],
            "notify_labels": ["person"], "storage_percent": 20, "storage_max_gb": 0, "record_mode": "hybrid",
            "ai_analysis": True, "ai_audio_transcription": True, "ptz_auto_tracking": True, "ptz_auto_patrol": False,
            "ptz_patrol_interval_s": 60, "continuous_hours": 48, "audio_cameras": [], "notice_enabled": False,
            "notice_repeat_hours": 12, "private_rooms": []}
CAMERA_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
MAX_AUDIO_CAMERAS = 64
MAX_PRIVATE_ROOMS = 50


class SettingsError(ValueError):
    pass


def load() -> dict:
    try:
        data = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        data = {}
    return {**DEFAULTS, **{k: v for k, v in (data if isinstance(data, dict) else {}).items() if k in DEFAULTS}}


def public(settings: dict) -> dict:
    return {**{k: v for k, v in settings.items() if k != SECRET}, "has_password": bool(settings.get(SECRET))}


def validate(body: dict, current: dict) -> dict:
    out = dict(current)
    out["enabled"] = bool(body.get("enabled", current["enabled"]))
    host = str(body.get("mqtt_host", current["mqtt_host"]) or "").strip()
    if host and not HOST_RE.match(host):
        raise SettingsError("nvr.error.host")
    if out["enabled"] and not host:
        raise SettingsError("nvr.error.host_required")
    out["mqtt_host"] = host
    try:
        port = int(body.get("mqtt_port", current["mqtt_port"]))
    except (TypeError, ValueError):
        raise SettingsError("nvr.error.port")
    if not 1 <= port <= 65535:
        raise SettingsError("nvr.error.port")
    out["mqtt_port"] = port
    topic = str(body.get("mqtt_topic", current["mqtt_topic"]) or "").strip()
    if not TOPIC_RE.match(topic):
        raise SettingsError("nvr.error.topic")
    out["mqtt_topic"] = topic
    out["mqtt_user"] = str(body.get("mqtt_user", current["mqtt_user"]) or "").strip()[:120]
    if body.get("clear_password"):
        out[SECRET] = ""
    elif str(body.get(SECRET) or ""):
        out[SECRET] = str(body[SECRET])[:256]
    out["mqtt_tls"] = bool(body.get("mqtt_tls", current["mqtt_tls"]))
    try:
        out["retention_days"] = max(1, min(365, int(body.get("retention_days", current["retention_days"]))))
        out["min_score"] = round(max(0.0, min(1.0, float(body.get("min_score", current["min_score"])))), 2)
        out["storage_percent"] = max(1, min(90, int(body.get("storage_percent", current.get("storage_percent", 20)))))
        out["storage_max_gb"] = max(0, min(100000, int(body.get("storage_max_gb", current.get("storage_max_gb", 0)))))
        out["continuous_hours"] = max(1, min(24 * 90, int(body.get("continuous_hours", current.get("continuous_hours", 48)))))
        out["ptz_patrol_interval_s"] = max(5, min(3600, int(body.get("ptz_patrol_interval_s", current.get("ptz_patrol_interval_s", 60)))))
    except (TypeError, ValueError):
        raise SettingsError("nvr.error.number")
    mode = str(body.get("record_mode", current.get("record_mode", "hybrid"))).lower()
    out["record_mode"] = mode if mode in ("continuous", "events", "hybrid") else "hybrid"
    for b_key in ("ai_analysis", "ai_audio_transcription", "ptz_auto_tracking", "ptz_auto_patrol"):
        out[b_key] = bool(body.get(b_key, current.get(b_key, DEFAULTS[b_key])))
    privacy(body, current, out)
    for key in ("labels", "notify_labels"):
        values = body.get(key, current[key])
        if not isinstance(values, list):
            raise SettingsError("nvr.error.labels")
        out[key] = [v for v in LABELS if v in values]
    return out


def privacy(body: dict, current: dict, out: dict) -> dict:
    cams = body.get("audio_cameras", current.get("audio_cameras", []))
    rooms = body.get("private_rooms", current.get("private_rooms", []))
    if not isinstance(cams, list) or not isinstance(rooms, list):
        raise SettingsError("nvr.error.privacy")
    if len(cams) > MAX_AUDIO_CAMERAS or any(not isinstance(c, str) or not CAMERA_RE.match(c) for c in cams):
        raise SettingsError("nvr.error.audio_cameras")
    clean_rooms = [" ".join(str(r).split())[:64] for r in rooms if isinstance(r, str) and str(r).strip()]
    if len(clean_rooms) > MAX_PRIVATE_ROOMS:
        raise SettingsError("nvr.error.private_rooms")
    out["audio_cameras"] = sorted(set(cams))
    out["private_rooms"] = sorted(set(clean_rooms))
    out["notice_enabled"] = bool(body.get("notice_enabled", current.get("notice_enabled", False)))
    try:
        out["notice_repeat_hours"] = max(1, min(168, int(body.get("notice_repeat_hours", current.get("notice_repeat_hours", 12)))))
    except (TypeError, ValueError):
        raise SettingsError("nvr.error.number")
    return out


def save(settings: dict) -> None:
    NVR_DIR.mkdir(parents=True, exist_ok=True)
    tmp = SETTINGS_FILE.with_suffix(".tmp")
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        json.dump(settings, handle, ensure_ascii=False, indent=1)
    os.replace(tmp, SETTINGS_FILE)
