from pathlib import Path

SIZES = ("s", "m", "l", "full")
TONES = ("cyan", "green", "blue", "violet", "amber", "red")
REFRESH_MIN, REFRESH_MAX = 1, 86400
FLAGS = ("essential", "urgent", "overlay", "personal", "standalone", "sticky", "immersive")


def clamp_refresh(value) -> int | None:
    if value in (None, "", False):
        return None
    try:
        seconds = int(value)
    except (TypeError, ValueError):
        return None
    return max(REFRESH_MIN, min(REFRESH_MAX, seconds))


def normalize(m: dict, folder: Path, system_dir: Path) -> None:
    m["priority"] = max(0, min(100, int(m.get("priority", 50))))
    m["size"] = m.get("size") if m.get("size") in SIZES else "m"
    m.setdefault("icon", "▣")
    m.setdefault("description", "")
    m.setdefault("intents", [])
    m.setdefault("replaces", [])
    m["chrome"] = m.get("chrome", True) is not False
    for flag in FLAGS:
        m[flag] = m.get(flag) is True
    m["tone"] = m.get("tone") if m.get("tone") in TONES else "cyan"
    m["refresh"] = clamp_refresh(m.get("refresh"))
    m["source"] = "system" if folder.is_relative_to(system_dir) else (m.get("source") if m.get("source") in ("ai", "user") else "user")
    m["dir"] = str(folder)
    m["has_css"] = (folder / "widget.css").exists()
    m["rev"] = str(int(max(p.stat().st_mtime for p in folder.glob("widget.*"))))
