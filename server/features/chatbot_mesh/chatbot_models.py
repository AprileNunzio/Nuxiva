from enum import Enum
from typing import List, Dict, Any
import time
from pydantic import BaseModel, Field

class ChatbotTone(str, Enum):
    FORMAL = "formal"
    CONCISE = "concise"
    FRIENDLY = "friendly"
    TECHNICAL = "technical"
    KID_SAFE = "kid_safe"
    POETIC = "poetic"

class ChannelType(str, Enum):
    WEB_CONSOLE = "web_console"
    TELEGRAM = "telegram"
    WHATSAPP = "whatsapp"
    DISCORD = "discord"
    SLACK = "slack"
    VOICE_HUD = "voice_hud"

class ChatMessagePayload(BaseModel):
    message_id: str = Field(default_factory=lambda: f"msg_{int(time.time()*1000)}")
    user_id: str
    agent_id: str
    channel: ChannelType = ChannelType.WEB_CONSOLE
    text: str
    attachments: List[str] = Field(default_factory=list)
    timestamp: float = Field(default_factory=time.time)

class ChatbotWidgetSpec(BaseModel):
    widget_id: str
    widget_type: str # es. "smart_switch", "cad_viewer", "weather_card", "milestone_progress", "code_snippet"
    title: str
    data: Dict[str, Any] = Field(default_factory=dict)

class ChatbotResponsePayload(BaseModel):
    response_id: str = Field(default_factory=lambda: f"resp_{int(time.time()*1000)}")
    agent_id: str
    user_id: str
    reply_text: str
    tools_invoked: List[Dict[str, Any]] = Field(default_factory=list)
    active_widgets: List[ChatbotWidgetSpec] = Field(default_factory=list)
    confidence: float = 1.0
    latency_ms: float = 0.0
    timestamp: float = Field(default_factory=time.time)

class UserAgentPersonalization(BaseModel):
    user_id: str
    agent_id: str
    custom_nickname: str = "" # Come l'utente chiama l'agente (es. "Alfred", "Assistente Personale")
    preferred_tone: ChatbotTone = ChatbotTone.FRIENDLY
    custom_persona_prompt: str = "" # Prompt personale dell'utente per questo agente
    custom_knowledge_notes: str = "" # Note e nozioni personali che solo questo utente condivide con l'agente
    allowed_tools: List[str] = Field(default_factory=list) # Tool attivi per questo utente
    enabled_widgets: List[str] = Field(default_factory=lambda: ["quick_actions", "system_status"]) # Widget abilitati per questo utente
    preferred_language: str = "" # Se vuota eredita NUXIVA_DEFAULT_LANGUAGE
    channel_handles: Dict[str, str] = Field(default_factory=dict) # es. {"telegram": "@user_handle"}
    updated_at: float = Field(default_factory=time.time)

class ChatHistoryRecord(BaseModel):
    sender: str # "user" o agent_id
    text: str
    timestamp: float = Field(default_factory=time.time)
    tools_used: List[str] = Field(default_factory=list)
    widget_ids: List[str] = Field(default_factory=list)
