from dataclasses import dataclass
from typing import Any


@dataclass
class AgentInferenceProfile:
    agent_id: str
    label: str = ""
    provider: str = "auto_fallback"
    endpoint: str = "http://127.0.0.1:11434"
    model: str = "default"
    temperature: float = 0.2
    timeout_seconds: int = 45

    def to_dict(self) -> dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "label": self.label,
            "provider": self.provider,
            "endpoint": self.endpoint,
            "model": self.model,
            "temperature": self.temperature,
            "timeout_seconds": self.timeout_seconds,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AgentInferenceProfile":
        return cls(
            agent_id=str(data.get("agent_id", "")),
            label=str(data.get("label", "")),
            provider=str(data.get("provider", "auto_fallback")),
            endpoint=str(data.get("endpoint", "http://127.0.0.1:11434")),
            model=str(data.get("model", "default")),
            temperature=float(data.get("temperature", 0.2)),
            timeout_seconds=int(data.get("timeout_seconds", 45)),
        )
