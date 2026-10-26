import importlib
import inspect
from pathlib import Path
from typing import Any, Dict, List, Optional
from server.core.reasoning.engines.base import BaseReasoningEngine
from server.features.llm_gateway.contracts import CognitiveEngineVersion

class EngineScanner:
    def __init__(self, engines_dir: Optional[Path] = None) -> None:
        self.engines_dir = engines_dir or Path(__file__).resolve().parent
        self._registry: Dict[CognitiveEngineVersion, BaseReasoningEngine] = {}

    def scan(self) -> Dict[CognitiveEngineVersion, BaseReasoningEngine]:
        self._registry.clear()
        for item in self.engines_dir.iterdir():
            if not item.is_dir() or item.name.startswith(("_", ".")):
                continue
            engine_file = item / "engine.py"
            if not engine_file.exists():
                continue
            module = None
            module_name = f"server.core.reasoning.engines.{item.name}.engine"
            try:
                module = importlib.import_module(module_name)
            except Exception:
                try:
                    import importlib.util
                    spec = importlib.util.spec_from_file_location(f"engine_{item.name}", engine_file)
                    if spec and spec.loader:
                        module = importlib.util.module_from_spec(spec)
                        spec.loader.exec_module(module)
                except Exception:
                    continue
            if not module:
                continue
            for _, obj in inspect.getmembers(module, inspect.isclass):
                if issubclass(obj, BaseReasoningEngine) and obj is not BaseReasoningEngine:
                    instance = obj()
                    self._registry[instance.version] = instance
                    ver_str = getattr(instance.version, "value", str(instance.version)).strip().lower()
                    self._registry[ver_str] = instance
                    self._registry[instance.key] = instance
                    # Folder and directory name aliases
                    self._registry[item.name.lower()] = instance
                    self._registry[item.name.lower().replace("_", ".")] = instance
                    # Shorthand version badge and suffix
                    badge = ver_str.removeprefix("nuxiva-")
                    self._registry[badge] = instance
                    suffix = badge.split("-")[-1]
                    self._registry[suffix] = instance
                    # Common ergonomic aliases
                    if any(k in badge for k in ("veloce", "flash", "fast")):
                        self._registry["fast"] = instance
                        self._registry["veloce"] = instance
                        self._registry["flash"] = instance
                        self._registry["5.0-flash"] = instance
                        self._registry["nuxiva-5.0-fast"] = instance
                    if "pro" in badge:
                        self._registry["pro"] = instance
                        self._registry["reasoning"] = instance
                        self._registry["ragionamento"] = instance
                        self._registry["5.0-pro"] = instance
                        self._registry["6.0-pro"] = instance
                    if "auto" in badge:
                        self._registry["auto"] = instance
                        self._registry["6.5-auto"] = instance
                    if "ultra" in badge:
                        self._registry["ultra"] = instance
                        self._registry["6.5-ultra"] = instance
                    if any(k in badge for k in ("empatico", "limbic", "empathetic")):
                        self._registry["empatico"] = instance
                        self._registry["empathetic"] = instance
                        self._registry["5.0-limbic"] = instance
                        self._registry["nuxiva-5.0-empatico"] = instance
                    if "legacy" in badge:
                        self._registry["legacy"] = instance
                        self._registry["4.2-legacy"] = instance
        return self._registry

    def get_engine(self, version: Any) -> Optional[BaseReasoningEngine]:
        if not self._registry:
            self.scan()
        if version is None:
            return None
        ver_str = getattr(version, "value", str(version)).strip().lower()
        if not ver_str:
            return None
        return self._registry.get(version) or self._registry.get(ver_str)

    def list_engines(self) -> List[BaseReasoningEngine]:
        if not self._registry:
            self.scan()
        unique = list({id(eng): eng for eng in self._registry.values()}.values())
        unique.sort(key=lambda x: (not getattr(x, "is_default", False), x.name))
        return unique

    def get_default_engine(self) -> BaseReasoningEngine:
        if not self._registry:
            self.scan()
        for eng in self.list_engines():
            if getattr(eng, "is_default", False):
                return eng
        return next(iter(self.list_engines()))

engine_scanner = EngineScanner()
