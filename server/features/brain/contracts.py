from typing import List, Optional
from pydantic import BaseModel, Field
from server.features.llm_gateway.contracts import CognitiveEngineVersion

class EngineVersionUpdateRequest(BaseModel):
    version: CognitiveEngineVersion
    reason: Optional[str] = Field(default=None, max_length=120)

class CognitiveEngineProfile(BaseModel):
    id: CognitiveEngineVersion
    name: str
    architecture: str
    latency_sla_ms: int
    vram_mb: int
    active: bool

class EngineVersionStatusResponse(BaseModel):
    current_configured: CognitiveEngineVersion
    active_runtime: CognitiveEngineVersion
    latency_sla_ms: int
    vram_mb: int
    engines: List[CognitiveEngineProfile]
    success: bool

class EngineTelemetryUpdate(BaseModel):
    version: CognitiveEngineVersion
    synaptic_latency_ms: float
    vram_allocated_mb: int
    complexity_psi: float
    neuromodulators: dict[str, float]
