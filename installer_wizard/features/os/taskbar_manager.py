from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from config import STATE_DIR

DEFAULT_PINNED: List[Dict[str, str]] = [
    {"app_id": "chat", "title_key": "app_chat", "icon": "chat"},
    {"app_id": "brain", "title_key": "app_brain", "icon": "brain"},
    {"app_id": "agency", "title_key": "app_agency", "icon": "terminal"},
    {"app_id": "settings", "title_key": "app_settings", "icon": "gear"},
]


class TaskbarManager:
    def __init__(self, state_file: Optional[Path] = None) -> None:
        self.state_file = state_file or (STATE_DIR / "taskbar.json")
        self._pinned: List[Dict[str, str]] = list(DEFAULT_PINNED)
        self._load()

    def _load(self) -> None:
        if not self.state_file.exists():
            return
        try:
            data = json.loads(self.state_file.read_text(encoding="utf-8"))
            pinned = data.get("pinned")
            if isinstance(pinned, list) and all(isinstance(item, dict) for item in pinned):
                self._pinned = [
                    {
                        "app_id": str(item.get("app_id", ""))[:64],
                        "title_key": str(item.get("title_key", ""))[:64],
                        "icon": str(item.get("icon", "app"))[:32],
                    }
                    for item in pinned
                    if item.get("app_id")
                ]
        except (OSError, ValueError):
            pass

    def _save(self) -> None:
        try:
            self.state_file.parent.mkdir(parents=True, exist_ok=True)
            payload = {"pinned": self._pinned}
            tmp = self.state_file.with_suffix(".tmp")
            tmp.write_text(json.dumps(payload), encoding="utf-8")
            tmp.replace(self.state_file)
        except OSError:
            pass

    def get_pinned_apps(self) -> List[Dict[str, Any]]:
        return list(self._pinned)

    def pin_app(self, app_id: str, title_key: str, icon: str = "app") -> bool:
        clean_id = str(app_id).strip()[:64]
        if not clean_id or any(item["app_id"] == clean_id for item in self._pinned):
            return False
        self._pinned.append({
            "app_id": clean_id,
            "title_key": str(title_key).strip()[:64] or f"app_{clean_id}",
            "icon": str(icon).strip()[:32] or "app",
        })
        self._save()
        return True

    def unpin_app(self, app_id: str) -> bool:
        clean_id = str(app_id).strip()
        initial_len = len(self._pinned)
        self._pinned = [item for item in self._pinned if item["app_id"] != clean_id]
        if len(self._pinned) != initial_len:
            self._save()
            return True
        return False

    def get_tray_status(self) -> Dict[str, Any]:
        from os_memory import memory_manager
        from os_notification import notification_manager
        return {
            "notifications_count": notification_manager.count(),
            "memory_percent": memory_manager.sample().get("percent", 0.0),
            "memory_state": memory_manager.sample().get("state", "normal"),
        }


taskbar_manager = TaskbarManager()
