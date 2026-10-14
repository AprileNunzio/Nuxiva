from typing import Dict, Any
from server.core.scanner.base import DiscoveryManifest
from server.web.widgets.base import BaseWidget

class WeatherWidget(BaseWidget):
    @property
    def manifest(self) -> DiscoveryManifest:
        return DiscoveryManifest(
            id=self._manifest_data.get("id", "weather"),
            name=self._manifest_data.get("name", "Weather & Climate"),
            category="widget",
            description=self._manifest_data.get("description", "Atmospheric forecast"),
            icon=self._manifest_data.get("icon", "⛅"),
            metadata={
                "render_type": self._manifest_data.get("render_type", "card"),
                "grid_span": self._manifest_data.get("grid_span", {"col": 1, "row": 1}),
            },
        )

    async def get_state(self, user_id: str = "") -> Dict[str, Any]:
        return {
            "city": "Rome",
            "temperature_celsius": 21.5,
            "condition": "Partly Cloudy",
            "humidity_percent": 55,
            "wind_speed_kmh": 12.0,
        }
