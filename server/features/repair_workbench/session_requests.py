from typing import List, Optional

from pydantic import BaseModel, Field, field_validator

from server.features.repair_workbench.text_types import (
    Identifier,
    LongText,
    ShortText,
)

MAX_FRAME_BASE64 = 6_000_000
GRID_SIZE_LIMIT = 4096


class StartSessionRequest(BaseModel):
    project_id: Identifier
    camera_id: Optional[str] = Field(default=None, max_length=128)
    camera_name: ShortText = ""
    language: ShortText = "it"


class AnalyzeFrameRequest(BaseModel):
    frame_base64: str = Field(min_length=16, max_length=MAX_FRAME_BASE64)
    grid: List[int] = Field(default_factory=list, max_length=GRID_SIZE_LIMIT)

    @field_validator("grid")
    @classmethod
    def _byte_values(cls, value: List[int]) -> List[int]:
        if any(not 0 <= v <= 255 for v in value):
            raise ValueError("grid values must be bytes")
        return value


class TeachComponentRequest(BaseModel):
    track_id: int = Field(ge=1, le=1_000_000)
    label: ShortText = Field(min_length=1)
    value: ShortText = ""


class ChatRequest(BaseModel):
    message: LongText = Field(min_length=1)
    agent_id: Optional[Identifier] = None


class EscalationRequest(BaseModel):
    requester_agent_id: Identifier
    specialty: ShortText = Field(min_length=2)
    justification: LongText = Field(min_length=2)
