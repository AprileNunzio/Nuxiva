import os
import sys
import json
import inspect
import hashlib
import importlib.util
from threading import RLock
from typing import TypeVar, Generic, Type, Dict, List, Optional, Any
from server.core.scanner.base import BaseDiscoverable, DiscoveryManifest
from server.core.scanner.security import ZeroTrustValidator, SecurityViolationError

T = TypeVar("T", bound=BaseDiscoverable)

class UniversalScanner(Generic[T]):
    def __init__(
        self,
        root_dir: str,
        target_filename: str,
        expected_type: Type[T],
        category: str,
        enable_security_check: bool = True,
    ) -> None:
        self.root_dir = os.path.abspath(root_dir)
        self.target_filename = target_filename
        self.expected_type = expected_type
        self.category = category
        self.enable_security_check = enable_security_check
        self._lock = RLock()
        self._cache: Dict[str, T] = {}
        self._manifests: Dict[str, DiscoveryManifest] = {}
        self._fingerprints: Dict[str, str] = {}
        self._rust_scanner = None
        self._init_rust_scanner()

    def _init_rust_scanner(self) -> None:
        try:
            import nuxiva_native
            if hasattr(nuxiva_native, "FastScanner"):
                self._rust_scanner = nuxiva_native.FastScanner()
        except ImportError:
            self._rust_scanner = None

    def _compute_hash(self, path: str) -> str:
        stat = os.stat(path)
        seed = f"{stat.st_size}_{stat.st_mtime}"
        if stat.st_size < 65536:
            with open(path, "rb") as f:
                seed += hashlib.sha256(f.read()).hexdigest()
        return seed

    def scan_all(self, force: bool = False) -> Dict[str, T]:
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
                target_path = os.path.join(full_dir, self.target_filename)
                if not os.path.exists(target_path):
                    continue

                manifest_path = os.path.join(full_dir, "manifest.json")
                file_hash = self._compute_hash(target_path)
                current_fp = self._fingerprints.get(item_dir)

                if not force and current_fp == file_hash and item_dir in self._cache:
                    active_ids.add(item_dir)
                    continue

                if self.enable_security_check and target_path.endswith(".py"):
                    with open(target_path, "r", encoding="utf-8") as src_file:
                        source_code = src_file.read()
                    is_valid, violations = ZeroTrustValidator.validate_source(source_code, target_path)
                    if not is_valid:
                        raise SecurityViolationError(f"Security check failed for {target_path}: {violations}")

                instance = self._load_instance(target_path, manifest_path, item_dir)
                if instance:
                    self._cache[item_dir] = instance
                    self._manifests[item_dir] = instance.manifest
                    self._fingerprints[item_dir] = file_hash
                    active_ids.add(item_dir)

            stale_keys = [k for k in self._cache.keys() if k not in active_ids]
            for stale_key in stale_keys:
                self._cache.pop(stale_key, None)
                self._manifests.pop(stale_key, None)
                self._fingerprints.pop(stale_key, None)

            return dict(self._cache)

    def _load_instance(self, target_path: str, manifest_path: str, item_id: str) -> Optional[T]:
        manifest_data: Dict[str, Any] = {}
        if os.path.exists(manifest_path):
            with open(manifest_path, "r", encoding="utf-8") as mf:
                manifest_data = json.load(mf)

        module_name = f"dynamic_nuxiva_{self.category}_{item_id}"
        spec = importlib.util.spec_from_file_location(module_name, target_path)
        if not spec or not spec.loader:
            return None

        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)

        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if inspect.isclass(attr) and issubclass(attr, self.expected_type) and attr is not self.expected_type:
                try:
                    if manifest_data:
                        instance = attr(manifest_data=manifest_data)
                    else:
                        instance = attr()
                    return instance
                except TypeError:
                    return attr()

        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if isinstance(attr, self.expected_type):
                return attr

        return None

    def get(self, item_id: str) -> Optional[T]:
        with self._lock:
            if not self._cache:
                self.scan_all()
            return self._cache.get(item_id)

    def list_all(self) -> List[T]:
        with self._lock:
            if not self._cache:
                self.scan_all()
            return list(self._cache.values())

    def get_manifests(self) -> List[DiscoveryManifest]:
        with self._lock:
            if not self._cache:
                self.scan_all()
            return list(self._manifests.values())

    def invalidate(self, item_id: str) -> None:
        with self._lock:
            self._cache.pop(item_id, None)
            self._manifests.pop(item_id, None)
            self._fingerprints.pop(item_id, None)
            if self._rust_scanner:
                self._rust_scanner.invalidate(item_id)

    def clear(self) -> None:
        with self._lock:
            self._cache.clear()
            self._manifests.clear()
            self._fingerprints.clear()
            if self._rust_scanner:
                self._rust_scanner.clear()
