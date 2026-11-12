from typing import List, Optional

from pydantic import BaseModel, Field

from server.features.llm_gateway.contracts import CognitiveEngineVersion


class EngineVersionUpdateRequest(BaseModel):
    version: CognitiveEngineVersion
    reason: Optional[str] = Field(default=None, max_length=120)


class EngineStrategy(BaseModel):
    kind: str
    candidates: int
    pick: str
    critic: bool
    wait_s: float


class CognitiveEngineProfile(BaseModel):
    id: CognitiveEngineVersion
    name: str
    architecture: str
    strategy: EngineStrategy
    active: bool


class EngineVersionStatusResponse(BaseModel):
    current_configured: CognitiveEngineVersion
    engines: List[CognitiveEngineProfile]
    success: bool


class OllamaProbeRequest(BaseModel):
    host: str = Field(default="http://127.0.0.1:11434")


class OllamaDiscoveredModel(BaseModel):
    name: str
    size: int = 0
    parameter_size: str = ""
    quantization_level: str = ""
    family: str = ""
    modified_at: str = ""


class OllamaProbeResponse(BaseModel):
    online: bool
    latency_ms: int = 0
    normalized_url: str
    models: List[OllamaDiscoveredModel] = Field(default_factory=list)
    error: Optional[str] = None


class OllamaHibernateRequest(BaseModel):
    local_targets_count: int = 0
    local_host: str = Field(default="http://127.0.0.1:11434")


class OllamaHibernateResponse(BaseModel):
    hibernated: bool
    status: str
    active_local_targets: int
    reason_code: str
