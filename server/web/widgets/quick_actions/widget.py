from typing import Dict, Any, List
from server.core.scanner.base import DiscoveryManifest
from server.web.widgets.base import BaseWidget

class QuickActionsWidget(BaseWidget):
    @property
    def manifest(self) -> DiscoveryManifest:
        return DiscoveryManifest(
            id=self._manifest_data.get("id", "quick_actions"),
            name=self._manifest_data.get("name", "Quick Actions"),
            category="widget",
            description=self._manifest_data.get("description", "Contextual action buttons"),
            icon=self._manifest_data.get("icon", "🕹️"),
            metadata={
                "render_type": self._manifest_data.get("render_type", "grid"),
                "grid_span": self._manifest_data.get("grid_span", {"col": 1, "row": 1}),
            },
        )

    async def get_state(self, user_id: str = "") -> Dict[str, Any]:
        return {
            "actions": [
                {"id": "mute_mic", "label": "Mute Mic", "icon": "🎙️"},
                {"id": "privacy_shield", "label": "Privacy Shield", "icon": "🛡️"},
                {"id": "lock_screen", "label": "Lock Workspace", "icon": "🔒"},
                {"id": "emergency_beacon", "label": "Emergency Beacon", "icon": "🚨"},
            ]
        }

    async def execute_action(self, action: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        return {"status": "success", "executed_action": action}
