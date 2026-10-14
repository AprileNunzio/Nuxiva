from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field

class CognitiveEngineVersion(str, Enum):
    LEGACY_4_2 = "nuxiva-4.2-legacy"
    VELOCE_5_0 = "nuxiva-5.0-veloce"
    EMPATICO_5_0 = "nuxiva-5.0-empatico"
    PRO_6_0 = "nuxiva-6.0-pro"
    ULTRA_6_5 = "nuxiva-6.5-ultra"
    AUTO_6_5 = "nuxiva-6.5-auto"

class LLMMessage(BaseModel):
    role: str
    content: str

class LLMRequest(BaseModel):
    model_name: str
    messages: List[LLMMessage]
    temperature: float = 0.2
    max_tokens: int = 2048
    stream: bool = False
    system_prompt: Optional[str] = None
    models: List[str] = Field(default_factory=list)
    pinned: str = ""
    component: str = ""
    reasoning_engine: Optional[CognitiveEngineVersion] = None

SYNTHETIC_MODEL = "deterministic-core-v1"

class LLMResponse(BaseModel):
    content: str
    model_used: str
    tokens_consumed: int
    duration_ms: float

    @property
    def is_synthetic(self) -> bool:
        return self.model_used == SYNTHETIC_MODEL

class EngineVersionChangeRequest(BaseModel):
    version: CognitiveEngineVersion

class EngineVersionResponse(BaseModel):
    current_version: CognitiveEngineVersion
    active_version: CognitiveEngineVersion
    latency_sla_ms: int
    vram_mb: int
    success: bool

