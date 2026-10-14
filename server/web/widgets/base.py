from abc import abstractmethod
from typing import Dict, Any, Optional
from server.core.scanner.base import BaseDiscoverable, DiscoveryManifest

class BaseWidget(BaseDiscoverable):
    def __init__(self, manifest_data: Optional[Dict[str, Any]] = None) -> None:
        self._manifest_data = manifest_data or {}

    @property
    @abstractmethod
    def manifest(self) -> DiscoveryManifest:
        pass

    @property
    def widget_id(self) -> str:
        return self.manifest.id

    @property
    def render_type(self) -> str:
        return self.manifest.metadata.get("render_type", "card")

    @abstractmethod
    async def get_state(self, user_id: str = "") -> Dict[str, Any]:
        pass

    async def execute_action(self, action: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        return {"status": "unsupported", "action": action}
