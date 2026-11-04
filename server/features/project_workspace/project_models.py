import time
import uuid
from enum import Enum
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

class MilestoneStatus(str, Enum):
    TODO = "TODO"
    IN_PROGRESS = "IN_PROGRESS"
    REVIEW = "REVIEW"
    DONE = "DONE"

class WarRoomMessageType(str, Enum):
    THOUGHT = "thought"          # Catena di ragionamento dell'agente
    ACTION = "action"            # Azione o esecuzione tool effettuata
    CRITIQUE = "critique"        # Revisione / critica da altro agente
    DELIVERABLE = "deliverable"  # File, disegno, codice o post generato
    ALERT = "alert"              # Notifica o intervento del Capo Agente
    USER_INPUT = "user_input"    # Intervento umano nella War Room

class ProjectMilestone(BaseModel):
    milestone_id: str = Field(default_factory=lambda: uuid.uuid4().hex[:8])
    title: str
    description: str = ""
    status: MilestoneStatus = MilestoneStatus.TODO
    progress: float = 0.0  # 0.0 a 1.0
    weight: float = 1.0
    assigned_agent_id: Optional[str] = None
    created_at: float = Field(default_factory=time.time)
    completed_at: Optional[float] = None

class WarRoomMessage(BaseModel):
    message_id: str = Field(default_factory=lambda: uuid.uuid4().hex[:10])
    timestamp: float = Field(default_factory=time.time)
    sender_id: str
    sender_name: str
    sender_role: str
    message_type: WarRoomMessageType
    content: str
    attachments: List[Dict[str, Any]] = Field(default_factory=list) # es. cad_preview, post_draft, diff
    metadata: Dict[str, Any] = Field(default_factory=dict)

class ProjectStateExtended(BaseModel):
    project_id: str
    name: str
    goal: str
    status: str = "ACTIVE" # "ACTIVE", "PAUSED", "COMPLETED", "ARCHIVED"
    visibility: str = "private"
    autonomous_247: bool = False
    completion_percentage: float = 0.0
    owner_id: str = "user_primary"
    assigned_agents: List[str] = Field(default_factory=list)
    lead_supervisor_id: str = "chief_supervisor"
    milestones: List[ProjectMilestone] = Field(default_factory=list)
    war_room_feed: List[WarRoomMessage] = Field(default_factory=list)
    loop_warnings_count: int = 0
    created_at: float
    updated_at: float

    @property
    def is_active(self) -> bool:
        return self.status == "ACTIVE"

    @property
    def chat_history(self) -> List[Dict[str, str]]:
        return [
            {
                "user" if m.message_type == WarRoomMessageType.USER_INPUT else "agent": m.content
            }
            for m in self.war_room_feed
        ]

