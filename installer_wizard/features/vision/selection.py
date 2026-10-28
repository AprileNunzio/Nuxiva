import json
import os
import time
from pathlib import Path

STATE = Path(os.environ.get("NUXIVA_WEBCAMS_FILE", "/var/lib/nuxiva/webcams.json"))
ENV_FILE = Path(os.environ.get("NUXIVA_STATE_ROOT", "/")).resolve() / "etc/nuxiva/nuxiva.env"
FALLBACK = os.environ.get("NUXIVA_CAMERA", "/dev/video0")
SIZES = {"640x480": (640, 480), "1280x720": (1280, 720), "1920x1080": (1920, 1080)}
_env_cache: dict = {"at": 0.0, "values": {}}


def _cfg(key: str, default: str) -> str:
    if key in os.environ and os.environ[key].strip():
        return os.environ[key].strip()
    now = time.time()
    if now - _env_cache["at"] > 5.0:
        vals: dict[str, str] = {}
        try:
            for line in ENV_FILE.read_text(encoding="utf-8", errors="ignore").splitlines():
                s = line.strip()
                if s and not s.startswith("#") and "=" in s:
                    k, v = s.split("=", 1)
                    vals[k.strip()] = v.strip().strip('"').strip("'")
        except OSError:
            pass
        _env_cache["at"] = now
        _env_cache["values"] = vals
    return _env_cache["values"].get(key, default)


def current() -> dict:
    try:
        raw = json.loads(STATE.read_text(encoding="utf-8")).get("selected") or {}
        stamp = STATE.stat().st_mtime
    except (OSError, ValueError, AttributeError):
        raw, stamp = {}, 0.0
    return {"rgb": raw.get("rgb") or FALLBACK, "ir": raw.get("ir"), "rgb_mode": raw.get("rgb_mode"),
            "ir_mode": raw.get("ir_mode"), "stamp": stamp}


def capture_size(mode: dict | None, cores: int) -> tuple[int, int]:
    wanted = _cfg("NUXIVA_CAMERA_RES", "auto")
    width, height = SIZES.get(wanted) or ((1280, 720) if cores >= 4 else (640, 480))
    if mode and mode.get("width") and mode.get("height"):
        width, height = min(width, mode["width"]), min(height, mode["height"])
    return width, height


def ir_enabled() -> bool:
    return _cfg("NUXIVA_IR_MODE", "auto").lower() != "off"


def affect_enabled() -> bool:
    return _cfg("NUXIVA_AFFECT", "on").lower() != "off"


def liveness_mode() -> str:
    value = _cfg("NUXIVA_LIVENESS", "advisory").lower()
    return value if value in ("off", "advisory", "strict") else "advisory"


def liveness_minimum() -> float:
    try:
        return max(0.1, min(0.95, float(_cfg("NUXIVA_LIVENESS_MIN", "0.55"))))
    except ValueError:
        return 0.55


def near_enter_ratio() -> float:
    try:
        return max(0.03, min(0.35, float(_cfg("NUXIVA_VISION_NEAR_RATIO", "0.08"))))
    except ValueError:
        return 0.08


def near_exit_ratio() -> float:
    enter = near_enter_ratio()
    default_exit = round(enter * 0.78, 4)
    try:
        return max(0.02, min(enter, float(_cfg("NUXIVA_VISION_NEAR_EXIT_RATIO", str(default_exit)))))
    except ValueError:
        return default_exit


def near_hold_seconds() -> float:
    try:
        return max(0.0, min(60.0, float(_cfg("NUXIVA_VISION_NEAR_HOLD_S", "6.0"))))
    except ValueError:
        return 6.0
