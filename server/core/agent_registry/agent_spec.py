import time
from typing import List

from pydantic import BaseModel, Field


class AgentCapabilitySpec(BaseModel):
    id: str
    name: str
    role_category: str
    avatar_icon: str
    description: str
    system_prompt: str
    tools: List[str] = Field(default_factory=list)
    widgets: List[str] = Field(default_factory=list)
    is_custom: bool = False
    created_at: float = Field(default_factory=time.time)
