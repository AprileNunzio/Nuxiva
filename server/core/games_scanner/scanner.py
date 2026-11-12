import os
import json
import time
import hashlib
from threading import RLock
from typing import Dict, List, Optional, Set
from server.core.games_scanner.contracts import (
    GameManifest,
    GameCommand,
    GameCapability,
    GameInspectionResult,
)
from server.core.games_scanner.introspector import GameIntrospector
from server.core.scanner.watcher import registry_watcher

class GamesScanner:
    def __init__(self, root_dir: Optional[str] = None) -> None:
        base_project = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
        if root_dir is None:
            root_dir = os.path.join(base_project, "giochi")
        self.root_dir = os.path.abspath(root_dir)
        self._status_file = os.path.join(base_project, "data", "games_registry_status.json")
        self._lock = RLock()
        self._cache: Dict[str, GameInspectionResult] = {}
        self._fingerprints: Dict[str, str] = {}
        self._disabled_game_ids: Set[str] = self._load_status()
        registry_watcher.register_scanner("games", self)

    def _load_status(self) -> Set[str]:
        if not os.path.exists(self._status_file):
            return set()
        try:
            with open(self._status_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                return set(data.get("disabled_games", []))
        except Exception:
            return set()

    def _save_status(self) -> None:
        payload = {"disabled_games": sorted(list(self._disabled_game_ids))}
        os.makedirs(os.path.dirname(self._status_file), exist_ok=True)
        with open(self._status_file, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)

    def _compute_dir_fingerprint(self, dir_path: str) -> str:
        stat = os.stat(dir_path)
        seed = f"{stat.st_mtime}_{stat.st_size}"
        targets = ["manifest.json", "metadata.json", "package.json"]
        for target in targets:
            full = os.path.join(dir_path, target)
            if os.path.exists(full):
                with open(full, "rb") as f:
                    seed += hashlib.sha256(f.read()).hexdigest()
        return hashlib.sha256(seed.encode()).hexdigest()

    def scan_all(self, force: bool = False) -> Dict[str, GameInspectionResult]:
        with self._lock:
            if not os.path.exists(self.root_dir) or not os.path.isdir(self.root_dir):
                return {}

            subdirs = [
                d for d in os.listdir(self.root_dir)
                if os.path.isdir(os.path.join(self.root_dir, d))
                and not d.startswith("_")
                and not d.startswith(".")
            ]

            active_ids = set()

            for item_dir in subdirs:
                full_dir = os.path.join(self.root_dir, item_dir)
                fingerprint = self._compute_dir_fingerprint(full_dir)
                current_fp = self._fingerprints.get(item_dir)

                if not force and current_fp == fingerprint and item_dir in self._cache:
                    active_ids.add(item_dir)
                    continue

                manifest, violations = GameIntrospector.introspect_directory(full_dir)
                if manifest:
                    manifest.is_active = (manifest.game_id not in self._disabled_game_ids)
                    inspection = GameInspectionResult(
                        manifest=manifest,
                        fingerprint=fingerprint,
                        last_scanned=time.time(),
                        violations=violations,
                    )
                    self._cache[item_dir] = inspection
                    self._fingerprints[item_dir] = fingerprint
                    active_ids.add(item_dir)

            stale_keys = [k for k in self._cache.keys() if k not in active_ids]
            for stale in stale_keys:
                self._cache.pop(stale, None)
                self._fingerprints.pop(stale, None)

            return dict(self._cache)

    def toggle_game_status(self, game_id: str, enabled: Optional[bool] = None) -> bool:
        with self._lock:
            game = self.get_game(game_id)
            if not game:
                raise KeyError(f"Game '{game_id}' not found")

            if enabled is None:
                new_state = not game.is_active
            else:
                new_state = bool(enabled)

            game.is_active = new_state
            if new_state:
                self._disabled_game_ids.discard(game.game_id)
            else:
                self._disabled_game_ids.add(game.game_id)

            self._save_status()
            return new_state

    def get_game(self, game_id: str) -> Optional[GameManifest]:
        with self._lock:
            if game_id not in self._cache:
                self.scan_all()
            inspection = self._cache.get(game_id)
            if inspection:
                return inspection.manifest
            for item in self._cache.values():
                if item.manifest.game_id == game_id:
                    return item.manifest
            return None

    def list_games(self, include_disabled: bool = True) -> List[GameManifest]:
        with self._lock:
            if not self._cache:
                self.scan_all()
            return [
                item.manifest for item in self._cache.values()
                if include_disabled or item.manifest.is_active
            ]

    def get_commands(self, game_id: str) -> List[GameCommand]:
        game = self.get_game(game_id)
        if not game or not game.is_active:
            return []
        return game.commands

    def get_capabilities(self, game_id: str) -> List[GameCapability]:
        game = self.get_game(game_id)
        if not game:
            return []
        return game.capabilities

    def invalidate(self, game_id: str) -> None:
        with self._lock:
            self._cache.pop(game_id, None)
            self._fingerprints.pop(game_id, None)

games_scanner = GamesScanner()
