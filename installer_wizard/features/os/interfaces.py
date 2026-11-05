from __future__ import annotations

from typing import Any, Dict, List, Optional, Protocol


class IWindowManager(Protocol):
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
        ...

    def update_state(self, window_id: str, state: str) -> bool:
        ...

    def update_geometry(self, window_id: str, x: int, y: int, width: int, height: int) -> bool:
        ...

    def close_window(self, window_id: str) -> bool:
        ...

    def get_windows(self) -> List[Dict[str, Any]]:
        ...


class IWallpaperManager(Protocol):
    def get_wallpaper(self) -> Dict[str, Any]:
        ...

    def set_wallpaper(self, mode: str, source: str, blur: bool = False) -> Dict[str, Any]:
        ...


class ITaskbarManager(Protocol):
    def get_pinned_apps(self) -> List[Dict[str, Any]]:
        ...

    def pin_app(self, app_id: str, title: str, icon: str) -> bool:
        ...

    def unpin_app(self, app_id: str) -> bool:
        ...

    def get_tray_status(self) -> Dict[str, Any]:
        ...
