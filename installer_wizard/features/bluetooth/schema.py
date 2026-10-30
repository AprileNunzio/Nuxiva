import re
import unicodedata

USE = ("auto", "preferred", "never")
LAYOUTS = ("auto", "it", "us", "gb", "es", "fr", "de", "pt", "ch")
PROFILES = ("auto", "quality", "headset")

SETTINGS: tuple[dict, ...] = (
    {"key": "alias", "group": "general", "type": "text", "default": "", "max": 40},
    {"key": "autoconnect", "group": "general", "type": "bool", "default": True},
    {"key": "output_use", "group": "audio_out", "type": "enum", "default": "auto", "options": USE},
    {"key": "volume", "group": "audio_out", "type": "int", "default": 60, "min": 0, "max": 100, "step": 5},
    {"key": "profile", "group": "audio_out", "type": "enum", "default": "auto", "options": PROFILES,
     "requires": ("audio_out", "audio_in")},
    {"key": "voice_input", "group": "audio_in", "type": "enum", "default": "auto", "options": USE},
    {"key": "mic_gain", "group": "audio_in", "type": "int", "default": 100, "min": 10, "max": 150, "step": 5},
    {"key": "pointer_speed", "group": "pointer", "type": "int", "default": 0, "min": -10, "max": 10, "step": 1},
    {"key": "natural_scroll", "group": "pointer", "type": "bool", "default": False},
    {"key": "left_handed", "group": "pointer", "type": "bool", "default": False},
    {"key": "keyboard_layout", "group": "keyboard", "type": "enum", "default": "auto", "options": LAYOUTS},
    {"key": "games_enabled", "group": "gamepad", "type": "bool", "default": True},
    {"key": "player_slot", "group": "gamepad", "type": "int", "default": 1, "min": 1, "max": 4, "step": 1},
    {"key": "deadzone", "group": "gamepad", "type": "int", "default": 8, "min": 0, "max": 40, "step": 1},
    {"key": "sensitivity", "group": "gamepad", "type": "int", "default": 5, "min": 1, "max": 10, "step": 1},
    {"key": "invert_y", "group": "gamepad", "type": "bool", "default": False},
    {"key": "vibration", "group": "gamepad", "type": "bool", "default": True},
)
BY_KEY = {s["key"]: s for s in SETTINGS}
LEGACY_ROLE = {"output": ("auto", "never"), "input": ("never", "auto"), "both": ("auto", "auto"),
               "off": ("never", "never")}
UNSAFE = re.compile(r"[<>\"'`\\{}]")


def applies(setting: dict, caps: list[str]) -> bool:
    if setting["group"] == "general":
        return True
    return all(c in caps for c in setting.get("requires", (setting["group"],)))


def public() -> list[dict]:
    return [{k: list(v) if isinstance(v, tuple) else v for k, v in s.items()} for s in SETTINGS]


def defaults() -> dict:
    return {s["key"]: s["default"] for s in SETTINGS}


def clean_text(value: object, limit: int) -> str:
    text = unicodedata.normalize("NFKC", str(value or ""))
    text = "".join(ch for ch in text if unicodedata.category(ch)[0] != "C")
    return " ".join(UNSAFE.sub("", text).split())[:limit]


def coerce(setting: dict, value: object) -> object:
    kind = setting["type"]
    if kind == "bool":
        if not isinstance(value, bool):
            raise ValueError(f"bluetooth_invalid_{setting['key']}")
        return value
    if kind == "int":
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError(f"bluetooth_invalid_{setting['key']}")
        return max(setting["min"], min(setting["max"], value))
    if kind == "enum":
        if value not in setting["options"]:
            raise ValueError(f"bluetooth_invalid_{setting['key']}")
        return value
    return clean_text(value, setting["max"])


def migrate(stored: dict) -> dict:
    data = {k: v for k, v in stored.items() if k in BY_KEY or k == "name"}
    role = stored.get("role")
    if role in LEGACY_ROLE:
        out, mic = LEGACY_ROLE[role]
        data.setdefault("output_use", out)
        data.setdefault("voice_input", mic)
    return data


def resolve(stored: dict) -> dict:
    merged = {**defaults(), **migrate(stored)}
    return {key: merged[key] for key in BY_KEY}


def update(stored: dict, changes: object) -> dict:
    if not isinstance(changes, dict) or len(changes) > len(SETTINGS):
        raise ValueError("bluetooth_invalid_settings")
    result = migrate(stored)
    for key, value in changes.items():
        setting = BY_KEY.get(key)
        if not setting:
            raise ValueError("bluetooth_unknown_setting")
        result[key] = coerce(setting, value)
    return result
