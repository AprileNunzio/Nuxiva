from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
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

    @property
    def icon(self) -> str:
        return "🧠"

    @abstractmethod
    async def process_latent_state(
        self,
        sensory_tensor: Any,
        limbic_vector: Optional[Any] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> Any:
        pass

    def get_flow_stages(self, query: str = "", context: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Restituisce la sequenza di stadi cognitivi da tracciare nel Flusso Cognitivo Completo."""
        return [
            {
                "kind": "reasoning",
                "name": f"{self.name} · {self.architecture}",
                "detail": f"Elaborazione cognitiva latente (SLA: {self.latency_sla_ms}ms, VRAM: {self.vram_mb}MB)",
                "label": "elaborazione",
            },
            {
                "kind": "decision",
                "name": "Sintesi & Allineamento",
                "detail": "Convergenza delle corsie corticali sul target semantico e collasso dello stato latente",
                "label": "consenso",
            },
        ]

    def get_profile(self, is_active: bool = False) -> Dict[str, Any]:
        ver_str = getattr(self.version, "value", str(self.version))
        badge = ver_str.removeprefix("nuxiva-")
        return {
            "id": ver_str,
            "version": badge,
            "badge": badge,
            "name": self.name,
            "architecture": self.architecture,
            "hint": self.architecture,
            "latency_sla_ms": self.latency_sla_ms,
            "sla_ms": self.latency_sla_ms,
            "vram_mb": self.vram_mb,
            "icon": getattr(self, "icon", "🧠"),
            "is_default": getattr(self, "is_default", False),
            "active": is_active,
        }

