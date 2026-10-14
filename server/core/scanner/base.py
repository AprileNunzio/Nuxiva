from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field

class DiscoveryManifest(BaseModel):
    id: str
    name: str
    version: str = "1.0.0"
    category: str
    description: str = ""
    icon: str = "⚡"
    parameters: Dict[str, Any] = Field(default_factory=dict)
    author: str = "Nuxiva System"
    is_active: bool = True
    metadata: Dict[str, Any] = Field(default_factory=dict)

class BaseDiscoverable(ABC):
    @property
    @abstractmethod
    def manifest(self) -> DiscoveryManifest:
        pass

    @property
    def id(self) -> str:
        return self.manifest.id

    @property
    def name(self) -> str:
        return self.manifest.name

    @property
    def category(self) -> str:
        return self.manifest.category

    async def initialize(self) -> None:
        pass

    async def teardown(self) -> None:
        pass
