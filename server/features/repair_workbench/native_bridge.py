import json
from typing import Any, Dict, List

from server.features.repair_workbench import fallback_engine


class WorkbenchEngine:
    def __init__(self) -> None:
        self._native = self._load_native()
        if self._native is None:
            self._gate = fallback_engine.PythonStabilityGate()
            self._tracker = fallback_engine.PythonComponentTracker()

    @staticmethod
    def _load_native() -> Any:
        try:
            import nuxiva_native
        except ImportError:
            return None
        factory = getattr(nuxiva_native, "RustWorkbenchTracker", None)
        return factory() if factory is not None else None

    @property
    def is_native(self) -> bool:
        return self._native is not None

    def observe_stability(self, grid: List[int]) -> str:
        if self._native is not None:
            return str(self._native.observe_stability(bytes(grid)))
        return self._gate.observe(grid)

    def update_tracks(self, detections: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if self._native is not None:
            return json.loads(self._native.update_tracks_json(json.dumps(detections)))
        return self._tracker.update(detections)

    def relabel(self, track_id: int, label: str) -> bool:
        if self._native is not None:
            return bool(self._native.relabel_track(track_id, label))
        return self._tracker.relabel(track_id, label)

    def validate_netlist(self, nets: List[Dict[str, Any]]) -> List[Dict[str, str]]:
        if self._native is not None:
            import nuxiva_native

            return json.loads(nuxiva_native.validate_netlist_json(json.dumps(nets)))
        return fallback_engine.validate_netlist(nets)

    def reset(self) -> None:
        if self._native is not None:
            self._native.reset()
            return
        self._gate.reset()
        self._tracker.reset()
