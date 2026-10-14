from abc import abstractmethod
from typing import Dict, Any
from server.core.scanner.base import BaseDiscoverable, DiscoveryManifest

class BaseAgentTool(BaseDiscoverable):
    @abstractmethod
    async def execute(self, **kwargs) -> Any:
        pass

    @property
    def tool_id(self) -> str:
        return self.manifest.id

    @property
    def description(self) -> str:
        return self.manifest.description

    @property
    def parameters(self) -> Dict[str, Any]:
        return self.manifest.parameters
