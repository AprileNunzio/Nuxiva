import time
from typing import Dict, Any
from server.core.scanner.base import DiscoveryManifest
from server.web.widgets.base import BaseWidget

class SystemStatusWidget(BaseWidget):
    @property
    def manifest(self) -> DiscoveryManifest:
        return DiscoveryManifest(
            id=self._manifest_data.get("id", "system_status"),
            name=self._manifest_data.get("name", "System Status"),
            category="widget",
            description=self._manifest_data.get("description", "Kernel telemetry"),
            icon=self._manifest_data.get("icon", "⚡"),
            metadata={
                "render_type": self._manifest_data.get("render_type", "metric"),
                "grid_span": self._manifest_data.get("grid_span", {"col": 1, "row": 1}),
            },
        )

    async def get_state(self, user_id: str = "") -> Dict[str, Any]:
        return {
            "kernel_status": "ONLINE",
            "uptime_seconds": 3600,
            "system_latency_ms": 1.2,
            "active_swarms": 4,
            "timestamp": time.time(),
        }

    async def execute_action(self, action: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        if action == "refresh":
            return await self.get_state()
        return {"status": "unsupported", "action": action}
