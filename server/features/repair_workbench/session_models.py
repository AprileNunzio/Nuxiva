from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, Field, field_validator

from server.features.repair_workbench.circuit_schemas import (
    CircuitSpec,
    ComponentCategory,
    PinRef,
)
from server.features.repair_workbench.text_types import (
    Identifier,
    LongText,
    MediumText,
    Reference,
    ShortText,
)


class ComponentHealth(str, Enum):
    OK = "ok"
    SUSPECT = "suspect"
    FAULT = "fault"
    UNKNOWN = "unknown"


class Message(BaseModel):
    key: Optional[ShortText] = None
    params: Dict[ShortText, ShortText] = Field(default_factory=dict, max_length=8)
    text: Optional[LongText] = None


class DetectedComponent(BaseModel):
    ref: Optional[Reference] = None
    label: ShortText
    value: ShortText = ""
    category: ComponentCategory = ComponentCategory.OTHER
    bbox: List[float] = Field(min_length=4, max_length=4)
    score: float = Field(default=0.5, ge=0.0, le=1.0)
    health: ComponentHealth = ComponentHealth.UNKNOWN
    notes: MediumText = ""

    @field_validator("bbox")
    @classmethod
    def _unit_box(cls, value: List[float]) -> List[float]:
        if any(not 0.0 <= v <= 1.0 for v in value):
            raise ValueError("bbox must be normalised")
        return value

    @property
    def key(self) -> str:
        return self.ref or self.label


class ConnectionHint(BaseModel):
    net: ShortText
    pins: List[PinRef] = Field(default_factory=list, max_length=64)


class VisionObservation(BaseModel):
    model_used: str = Field(default="", max_length=200)
    title: ShortText = ""
    board_kind: ShortText = ""
    summary: LongText = ""
    characteristics: List[MediumText] = Field(default_factory=list, max_length=24)
    components: List[DetectedComponent] = Field(default_factory=list, max_length=200)
    connections: List[ConnectionHint] = Field(default_factory=list, max_length=200)
    advice: List[LongText] = Field(default_factory=list, max_length=8)


class ARComponentPopup(BaseModel):
    track_id: int
    key: ShortText
    label: ShortText
    value: ShortText = ""
    category: ComponentCategory = ComponentCategory.OTHER
    bbox: List[float]
    health: ComponentHealth = ComponentHealth.UNKNOWN
    notes: MediumText = ""
    expected_voltages: Dict[ShortText, float] = Field(default_factory=dict)
    taught: bool = False


class BoardDossier(BaseModel):
    title: ShortText = ""
    board_kind: ShortText = ""
    summary: LongText = ""
    characteristics: List[MediumText] = Field(default_factory=list)
    anomalies: List[Message] = Field(default_factory=list)
    component_count: int = 0


class AgentNote(BaseModel):
    agent_id: Identifier
    message: Message


class WorkbenchSession(BaseModel):
    vision_model: str = Field(default="", max_length=200)
    session_id: Identifier
    project_id: Identifier
    owner_id: Identifier
    camera_id: str = ""
    camera_name: ShortText = ""
    language: ShortText = "it"
    created_at: float
    updated_at: float
    scene_state: ShortText = "warmup"
    frame_count: int = 0
    dossier: BoardDossier = Field(default_factory=BoardDossier)
    popups: List[ARComponentPopup] = Field(default_factory=list)
    circuit: CircuitSpec = Field(default_factory=CircuitSpec)
    expected_voltages: Dict[ShortText, float] = Field(default_factory=dict)
    advice: List[Message] = Field(default_factory=list)
    notes: List[AgentNote] = Field(default_factory=list)
    aliases: Dict[ShortText, ShortText] = Field(default_factory=dict)
    taught_values: Dict[ShortText, ShortText] = Field(default_factory=dict)
