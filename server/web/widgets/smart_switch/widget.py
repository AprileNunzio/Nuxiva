from typing import Dict, Any
from server.core.scanner.base import DiscoveryManifest
from server.web.widgets.base import BaseWidget

class SmartSwitchWidget(BaseWidget):
    def __init__(self, manifest_data=None):
        super().__init__(manifest_data)
        self._state = False

    @property
    def manifest(self) -> DiscoveryManifest:
        return DiscoveryManifest(
            id=self._manifest_data.get("id", "smart_switch"),
            name=self._manifest_data.get("name", "Smart Switch"),
            category="widget",
            description=self._manifest_data.get("description", "IoT lighting and devices"),
            icon=self._manifest_data.get("icon", "💡"),
            metadata={
                "render_type": self._manifest_data.get("render_type", "toggle"),
                "grid_span": self._manifest_data.get("grid_span", {"col": 1, "row": 1}),
            },
        )

    async def get_state(self, user_id: str = "") -> Dict[str, Any]:
        return {
            "is_on": self._state,
            "device_name": "Living Room Light",
            "brightness_percent": 80 if self._state else 0,
        }

    async def execute_action(self, action: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        if action == "toggle":
            self._state = not self._state
            return {"status": "success", "is_on": self._state}
        elif action == "set":
            self._state = bool(payload.get("value", False))
            return {"status": "success", "is_on": self._state}
        return {"status": "unsupported", "action": action}
