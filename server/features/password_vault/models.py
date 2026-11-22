from enum import Enum
from typing import List, Optional
import time
from pydantic import BaseModel, Field


class SecretCategory(str, Enum):
    SSH = "ssh"
    WIFI = "wifi"
    WEB = "web"
    DEVICE = "device"
    API_KEY = "api_key"
    DATABASE = "database"
    OTHER = "other"


class VaultUnlockRequest(BaseModel):
    master_password: str = Field(..., min_length=4, max_length=256)
    ttl_seconds: int = Field(900, ge=60, le=86400)


class VaultEntryCreate(BaseModel):
    label: str = Field(..., min_length=1, max_length=120)
    category: SecretCategory = SecretCategory.WEB
    host_or_url: str = Field("", max_length=256)
    port: Optional[int] = Field(None, ge=1, le=65535)
    username: str = Field("", max_length=128)
    secret: str = Field("", max_length=4096)
    extra_secret: str = Field("", max_length=8192)  # es. SSH private key o token secondario
    notes: str = Field("", max_length=2000)
    tags: List[str] = Field(default_factory=list)


class VaultEntryMetadata(BaseModel):
    entry_id: str
    label: str
    category: SecretCategory
    host_or_url: str = ""
    port: Optional[int] = None
    username: str = ""
    has_secret: bool = False
    has_extra_secret: bool = False
    masked_preview: str = ""
    notes: str = ""
    tags: List[str] = Field(default_factory=list)
    created_at: float = Field(default_factory=time.time)
    updated_at: float = Field(default_factory=time.time)


class VaultEntryRevealed(VaultEntryMetadata):
    secret: str = ""
    extra_secret: str = ""


class VaultStatusResponse(BaseModel):
    user_id: str
    initialized: bool
    unlocked: bool
    entry_count: int
    expires_at: Optional[float] = None
