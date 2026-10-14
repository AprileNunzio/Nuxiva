import importlib
import inspect
from pathlib import Path
from typing import Dict, List, Optional, Type
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
            module_name = f"server.core.reasoning.engines.{item.name}.engine"
            module = importlib.import_module(module_name)
            for _, obj in inspect.getmembers(module, inspect.isclass):
                if issubclass(obj, BaseReasoningEngine) and obj is not BaseReasoningEngine:
                    instance = obj()
                    self._registry[instance.version] = instance
        return self._registry

    def get_engine(self, version: CognitiveEngineVersion) -> Optional[BaseReasoningEngine]:
        if not self._registry:
            self.scan()
        return self._registry.get(version)

    def list_engines(self) -> List[BaseReasoningEngine]:
        if not self._registry:
            self.scan()
        return list(self._registry.values())

    def get_default_engine(self) -> BaseReasoningEngine:
        if not self._registry:
            self.scan()
        for eng in self._registry.values():
            if eng.is_default:
                return eng
        return next(iter(self._registry.values()))

engine_scanner = EngineScanner()
