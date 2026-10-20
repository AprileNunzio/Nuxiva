from typing import Dict, Any
from server.core.scanner.base import DiscoveryManifest
from server.web.widgets.base import BaseWidget

class BrainActivityWidget(BaseWidget):
    @property
    def manifest(self) -> DiscoveryManifest:
        return DiscoveryManifest(
            id=self._manifest_data.get("id", "brain_activity"),
            name=self._manifest_data.get("name", "Brain Activity Latency"),
            category="widget",
            description=self._manifest_data.get("description", "Cognitive latency metrics"),
            icon=self._manifest_data.get("icon", "🧠"),
            metadata={
                "render_type": self._manifest_data.get("render_type", "graph"),
                "grid_span": self._manifest_data.get("grid_span", {"col": 2, "row": 1}),
            },
        )

    async def get_state(self, user_id: str = "") -> Dict[str, Any]:
        return {
            "active_engine": "nuxiva-6.5-ultra",
            "average_latency_ms": 320,
            "latent_spikes_per_sec": 1420,
            "vram_usage_mb": 11500,
            "stability_index": 0.994,
        }
