from __future__ import annotations

import json
import re
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from config import STATE_DIR

ID_PATTERN = re.compile(r"^[a-zA-Z0-9_\-\.]{1,64}$")


@dataclass
class WindowState:
    id: str
    title: str
    app_id: str
    x: int
    y: int
    width: int
    height: int
    state: str
    z_index: int
    created_at: float
    updated_at: float

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class WindowManager:
    def __init__(self, state_file: Optional[Path] = None) -> None:
        self.state_file = state_file or (STATE_DIR / "windows.json")
        self._windows: Dict[str, WindowState] = {}
        self._highest_z: int = 100
        self._load()

    def _sanitize_id(self, val: str) -> str:
        s = str(val).strip()
        if not ID_PATTERN.fullmatch(s):
            raise ValueError("Invalid identifier")
        return s

    def _sanitize_title(self, val: str) -> str:
        s = str(val).strip()
        return s[:80] if s else "Untitled"

    def _load(self) -> None:
        if not self.state_file.exists():
            return
        try:
            data = json.loads(self.state_file.read_text(encoding="utf-8"))
            for item in data.get("windows", []):
                w = WindowState(**item)
                self._windows[w.id] = w
                if w.z_index > self._highest_z:
                    self._highest_z = w.z_index
        except (OSError, ValueError, TypeError):
            self._windows = {}

    def _save(self) -> None:
        try:
            self.state_file.parent.mkdir(parents=True, exist_ok=True)
            payload = {"windows": [w.to_dict() for w in self._windows.values()]}
            tmp = self.state_file.with_suffix(".tmp")
            tmp.write_text(json.dumps(payload), encoding="utf-8")
            tmp.replace(self.state_file)
        except OSError:
            pass

    def register_window(
        self,
        window_id: str,
        title: str,
        app_id: str,
        width: int = 800,
        height: int = 600,
        x: Optional[int] = None,
        y: Optional[int] = None,
    ) -> Dict[str, Any]:
        clean_id = self._sanitize_id(window_id)
        clean_title = self._sanitize_title(title)
        clean_app = self._sanitize_id(app_id)
        now = time.time()
        self._highest_z += 1

        w = WindowState(
            id=clean_id,
            title=clean_title,
            app_id=clean_app,
            x=x if x is not None else 60 + (len(self._windows) * 30) % 300,
            y=y if y is not None else 60 + (len(self._windows) * 30) % 200,
            width=max(320, min(3840, width)),
            height=max(200, min(2160, height)),
            state="normal",
            z_index=self._highest_z,
            created_at=now,
            updated_at=now,
        )
        self._windows[clean_id] = w
        self._save()
        return w.to_dict()

    def focus_window(self, window_id: str) -> bool:
        clean_id = self._sanitize_id(window_id)
        w = self._windows.get(clean_id)
        if not w:
            return False
        self._highest_z += 1
        w.z_index = self._highest_z
        if w.state == "minimized":
            w.state = "normal"
        w.updated_at = time.time()
        self._save()
        return True

    def update_state(self, window_id: str, state: str) -> bool:
        clean_id = self._sanitize_id(window_id)
        if state not in ("normal", "minimized", "maximized"):
            raise ValueError("Invalid window state")
        w = self._windows.get(clean_id)
        if not w:
            return False
        w.state = state
        w.updated_at = time.time()
        self._save()
        return True

    def update_geometry(self, window_id: str, x: int, y: int, width: int, height: int) -> bool:
        clean_id = self._sanitize_id(window_id)
        w = self._windows.get(clean_id)
        if not w:
            return False
        w.x = x
        w.y = y
        w.width = max(320, min(3840, width))
        w.height = max(200, min(2160, height))
        w.updated_at = time.time()
        self._save()
        return True

    def close_window(self, window_id: str) -> bool:
        clean_id = self._sanitize_id(window_id)
        if clean_id in self._windows:
            del self._windows[clean_id]
            self._save()
            return True
        return False

    def get_windows(self) -> List[Dict[str, Any]]:
        return [w.to_dict() for w in sorted(self._windows.values(), key=lambda w: w.z_index)]


window_manager = WindowManager()
