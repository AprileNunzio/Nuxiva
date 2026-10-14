from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from server.features.llm_gateway.contracts import CognitiveEngineVersion

class BaseReasoningEngine(ABC):
    @property
    @abstractmethod
    def version(self) -> CognitiveEngineVersion:
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @property
    @abstractmethod
    def architecture(self) -> str:
        pass

    @property
    @abstractmethod
    def latency_sla_ms(self) -> int:
        pass

    @property
    @abstractmethod
    def vram_mb(self) -> int:
        pass

    @property
    def is_default(self) -> bool:
        return False

    @abstractmethod
    async def process_latent_state(
        self,
        sensory_tensor: Any,
        limbic_vector: Optional[Any] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> Any:
        pass

    def get_profile(self, is_active: bool = False) -> Dict[str, Any]:
        return {
            "id": self.version.value,
            "name": self.name,
            "architecture": self.architecture,
            "latency_sla_ms": self.latency_sla_ms,
            "vram_mb": self.vram_mb,
            "active": is_active,
        }
