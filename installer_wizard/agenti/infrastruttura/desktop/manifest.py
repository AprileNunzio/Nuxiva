import re
from pathlib import Path

SIZES = ("s", "m", "l", "full")
TONES = ("cyan", "green", "blue", "violet", "amber", "red")
REFRESH_MIN, REFRESH_MAX = 1, 86400
CATEGORIES = ("safety", "conversation", "personal", "home", "work", "media", "info", "system", "ambient")
MEDIA = ("audio", "video")
SIMPLE_MODES = ("collapse", "open")
ICON_RE = re.compile(r"^[a-z0-9_]{1,24}$")
FLAGS = ("essential", "urgent", "overlay", "personal", "standalone", "sticky", "immersive")


def clamp_refresh(value) -> int | None:
    if value in (None, "", False):
        return None
    try:
        seconds = int(value)
    except (TypeError, ValueError):
        return None
    return max(REFRESH_MIN, min(REFRESH_MAX, seconds))


def clean_cost(raw) -> dict | None:
    if not isinstance(raw, dict):
        return None
    out = {}
    for key in ("gpu", "cpu"):
        try:
            out[key] = max(0.5, min(8.0, float(raw.get(key, 2))))
        except (TypeError, ValueError):
            out[key] = 2.0
    return out


def clean_simple(raw) -> dict:
    raw = raw if isinstance(raw, dict) else {}
    icon = raw.get("icon") if isinstance(raw.get("icon"), str) and ICON_RE.match(raw["icon"]) else "info"
    mode = raw.get("mode") if raw.get("mode") in SIMPLE_MODES else "open"
    return {"icon": icon, "mode": mode}


def normalize(m: dict, folder: Path, system_dirs: tuple[Path, ...]) -> None:
    m["priority"] = max(0, min(100, int(m.get("priority", 50))))
    m["size"] = m.get("size") if m.get("size") in SIZES else "m"
    m.setdefault("icon", "▣")
    m.setdefault("description", "")
    m.setdefault("intents", [])
    m.setdefault("replaces", [])
    m["chrome"] = m.get("chrome", True) is not False
    for flag in FLAGS:
        m[flag] = m.get(flag) is True
    m["category"] = m.get("category") if m.get("category") in CATEGORIES else "info"
    m["media"] = m.get("media") if m.get("media") in MEDIA else None
    m["exclusive"] = m.get("exclusive") if m.get("exclusive") in MEDIA else None
    m["simple"] = clean_simple(m.get("simple"))
    m["tone"] = m.get("tone") if m.get("tone") in TONES else "cyan"
    m["refresh"] = clamp_refresh(m.get("refresh"))
    m["cost"] = clean_cost(m.get("cost"))
    m["source"] = "system" if any(folder.is_relative_to(d) for d in system_dirs) else (m.get("source") if m.get("source") in ("ai", "user") else "user")
    m["dir"] = str(folder)
    m["has_css"] = (folder / "widget.css").exists()
    m["rev"] = str(int(max(p.stat().st_mtime for p in folder.glob("widget.*"))))
