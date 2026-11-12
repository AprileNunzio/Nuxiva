from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional

from config import STATE_DIR

VALID_MODES = {"ambient_gradient", "hologram_particles", "deep_space", "minimal_dark", "custom_image"}


class WallpaperManager:
    def __init__(self, state_file: Optional[Path] = None) -> None:
        self.state_file = state_file or (STATE_DIR / "wallpaper.json")
        self._mode: str = "ambient_gradient"
        self._source: str = "default"
        self._blur: bool = False
        self._load()

    def _load(self) -> None:
        if not self.state_file.exists():
            return
        try:
            data = json.loads(self.state_file.read_text(encoding="utf-8"))
            mode = data.get("mode")
            if mode in VALID_MODES:
                self._mode = mode
            self._source = str(data.get("source", "default"))[:256]
            self._blur = bool(data.get("blur", False))
        except (OSError, ValueError):
            pass

    def _save(self) -> None:
        try:
            self.state_file.parent.mkdir(parents=True, exist_ok=True)
            payload = {"mode": self._mode, "source": self._source, "blur": self._blur}
            tmp = self.state_file.with_suffix(".tmp")
            tmp.write_text(json.dumps(payload), encoding="utf-8")
            tmp.replace(self.state_file)
        except OSError:
            pass

    def get_wallpaper(self) -> Dict[str, Any]:
        return {
            "mode": self._mode,
            "source": self._source,
            "blur": self._blur,
            "available_modes": sorted(list(VALID_MODES)),
        }

    def set_wallpaper(self, mode: str, source: str = "default", blur: bool = False) -> Dict[str, Any]:
        if mode not in VALID_MODES:
            raise ValueError(f"Invalid wallpaper mode: {mode}")
        clean_source = str(source).strip()[:256]
        self._mode = mode
        self._source = clean_source
        self._blur = bool(blur)
        self._save()
        return self.get_wallpaper()


wallpaper_manager = WallpaperManager()
