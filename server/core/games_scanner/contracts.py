from enum import Enum
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

class CommandInputType(str, Enum):
    VOICE = "voice"
    UI_ACTION = "ui_action"
    SHORTCUT = "shortcut"
    API_CALL = "api_call"

class CapabilityCategory(str, Enum):
    RENDERING = "rendering"
    AUDIO = "audio"
    ARTIFICIAL_INTELLIGENCE = "ai"
    INPUT = "input"
    NETWORK = "network"
    STORAGE = "storage"
    PHYSICS = "physics"

class GameCommand(BaseModel):
    command_id: str
    name_key: str
    description_key: str
    input_types: List[CommandInputType] = Field(default_factory=list)
    voice_triggers: List[str] = Field(default_factory=list)
    parameters: Dict[str, Any] = Field(default_factory=dict)
    requires_confirmation: bool = False
    is_async: bool = False

class GameCapability(BaseModel):
    capability_id: str
    category: CapabilityCategory
    name_key: str
    description_key: str
    enabled: bool = True
    metadata: Dict[str, Any] = Field(default_factory=dict)

class GameManifest(BaseModel):
    game_id: str
    name: str
    version: str = "1.0.0"
    category: str = "games"
    description: str = ""
    icon: str = "🎮"
    entrypoint: str
    tech_stack: List[str] = Field(default_factory=list)
    commands: List[GameCommand] = Field(default_factory=list)
    capabilities: List[GameCapability] = Field(default_factory=list)
    directory_path: str
    is_active: bool = True
    metadata: Dict[str, Any] = Field(default_factory=dict)

class CommandExecutionRequest(BaseModel):
    command_id: str
    parameters: Dict[str, Any] = Field(default_factory=dict)
    session_id: Optional[str] = None
    user_id: Optional[str] = None

class CommandExecutionResult(BaseModel):
    success: bool
    command_id: str
    result_data: Dict[str, Any] = Field(default_factory=dict)
    feedback_speech_key: Optional[str] = None
    error_message: Optional[str] = None

class GameInspectionResult(BaseModel):
    manifest: GameManifest
    fingerprint: str
    last_scanned: float
    violations: List[str] = Field(default_factory=list)
