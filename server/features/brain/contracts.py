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
