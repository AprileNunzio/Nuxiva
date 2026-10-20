from __future__ import annotations

import json
import logging
import os
import re
import tempfile
import threading
import time
import unicodedata
from pathlib import Path
from typing import Any, Callable, Dict, Optional

log = logging.getLogger("nuxiva.mesh.registry")

NODE_ID_PATTERN = re.compile(r"^[A-Za-z0-9._:@-]{1,128}$")
MAX_NAME_LENGTH = 64
_CONTROL_CHARS = re.compile(r"[\u0000-\u001F\u007F-\u009F​-‏‪-‮⁦-⁩﻿]")
_REGISTRY_FILE = "mesh_nodes.json"
_SCHEMA_VERSION = 1


class NodeRegistryError(ValueError):
    pass


def default_state_dir() -> Path:
    explicit = os.environ.get("NUXIVA_STATE_DIR")
    if explicit:
        return Path(explicit)
    if os.environ.get("NUXIVA_DEMO") == "1":
        return Path(tempfile.gettempdir()) / "nuxiva-demo" / "var" / "lib" / "nuxiva"
    return Path("/var/lib/nuxiva")


def validate_node_id(node_id: str) -> str:
    if not isinstance(node_id, str) or not NODE_ID_PATTERN.match(node_id):
        raise NodeRegistryError("invalid_node_id")
    return node_id


def normalize_node_name(raw: str) -> str:
    if not isinstance(raw, str):
        raise NodeRegistryError("invalid_node_name")
    name = _CONTROL_CHARS.sub("", unicodedata.normalize("NFKC", raw)).strip()
    name = re.sub(r"\s+", " ", name)
    if not name or len(name) > MAX_NAME_LENGTH:
        raise NodeRegistryError("invalid_node_name")
    return name


class NodeRegistry:
    def __init__(self, state_dir_resolver: Callable[[], Path] = default_state_dir) -> None:
        self._resolver = state_dir_resolver
        self._lock = threading.RLock()
        self._nodes: Optional[Dict[str, Dict[str, Any]]] = None

    @property
    def path(self) -> Path:
        return self._resolver() / _REGISTRY_FILE

    def custom_name(self, node_id: str) -> Optional[str]:
        with self._lock:
            return self._data().get(node_id, {}).get("name")

    def set_custom_name(self, node_id: str, raw_name: str) -> str:
        validate_node_id(node_id)
        name = normalize_node_name(raw_name)
        with self._lock:
            entry = self._data().setdefault(node_id, {})
            entry["name"] = name
            entry["name_updated_at"] = time.time()
            self._persist()
        return name

    def binding(self, node_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            stored = self._data().get(node_id, {}).get("binding")
            return dict(stored) if isinstance(stored, dict) else None

    def bindings(self) -> Dict[str, Dict[str, Any]]:
        with self._lock:
            return {
                node_id: dict(entry["binding"])
                for node_id, entry in self._data().items()
                if isinstance(entry.get("binding"), dict)
            }

    def set_binding(self, node_id: str, binding: Dict[str, Any]) -> None:
        validate_node_id(node_id)
        with self._lock:
            entry = self._data().setdefault(node_id, {})
            entry["binding"] = {
                "parent_node_id": str(binding["parent_node_id"]),
                "parent_ip": str(binding["parent_ip"]),
                "satellite_ip": str(binding["satellite_ip"]),
                "stream_type": str(binding["stream_type"]),
                "updated_at": time.time(),
            }
            self._persist()

    def forget(self, node_id: str) -> None:
        with self._lock:
            if self._data().pop(node_id, None) is not None:
                self._persist()

    def _data(self) -> Dict[str, Dict[str, Any]]:
        if self._nodes is None:
            self._nodes = self._load()
        return self._nodes

    def _load(self) -> Dict[str, Dict[str, Any]]:
        path = self.path
        if not path.exists():
            return {}
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            quarantine = path.with_suffix(f".corrupt-{int(time.time())}")
            log.error("Registro nodi illeggibile (%s), isolato in %s", exc, quarantine)
            path.replace(quarantine)
            return {}
        nodes = payload.get("nodes") if isinstance(payload, dict) else None
        if not isinstance(nodes, dict):
            log.error("Registro nodi con schema non valido, ignorato: %s", path)
            return {}
        return {
            node_id: entry
            for node_id, entry in nodes.items()
            if isinstance(node_id, str) and NODE_ID_PATTERN.match(node_id) and isinstance(entry, dict)
        }

    def _persist(self) -> None:
        path = self.path
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps({"version": _SCHEMA_VERSION, "nodes": self._nodes or {}}, ensure_ascii=False, indent=2)
        fd, tmp_name = tempfile.mkstemp(prefix=".mesh_nodes.", suffix=".tmp", dir=str(path.parent))
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
            os.chmod(tmp_name, 0o600)
            os.replace(tmp_name, path)
        except BaseException:
            if os.path.exists(tmp_name):
                os.unlink(tmp_name)
            raise
