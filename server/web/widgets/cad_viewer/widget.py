from typing import Dict, Any
from server.core.scanner.base import DiscoveryManifest
from server.web.widgets.base import BaseWidget

class CadViewerWidget(BaseWidget):
    @property
    def manifest(self) -> DiscoveryManifest:
        return DiscoveryManifest(
            id=self._manifest_data.get("id", "cad_viewer"),
            name=self._manifest_data.get("name", "CAD Vector Viewer"),
            category="widget",
            description=self._manifest_data.get("description", "Interactive CAD viewer"),
            icon=self._manifest_data.get("icon", "📐"),
            metadata={
                "render_type": self._manifest_data.get("render_type", "canvas"),
                "grid_span": self._manifest_data.get("grid_span", {"col": 2, "row": 2}),
            },
        )

    async def get_state(self, user_id: str = "") -> Dict[str, Any]:
        return {
            "active_file": None,
            "layers": [],
            "zoom_level": 1.0,
            "entities_count": 0,
        }

    async def execute_action(self, action: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        if action == "zoom":
            return {"status": "unavailable", "reason": "No CAD document loaded"}
        return {"status": "unsupported", "action": action}
