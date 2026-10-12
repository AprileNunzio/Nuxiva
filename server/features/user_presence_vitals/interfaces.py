from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
import time

class EmergencySeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    FATAL_ARREST = "fatal_arrest"

class EmergencyContact(BaseModel):
    contact_id: str = Field(..., min_length=2, max_length=64)
    name: str = Field(..., min_length=2, max_length=128)
    relationship: str = Field(..., min_length=2, max_length=64)
    phone_number: str = Field(..., pattern=r"^\+?[0-9\s\-]{6,20}$")
    email: Optional[str] = Field(None, pattern=r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")
    notify_by_sms: bool = True
    notify_by_call: bool = True
    priority_order: int = Field(1, ge=1, le=10)

class EmergencyVitalsThresholds(BaseModel):
    cardiac_arrest_min_bpm: float = Field(28.0, ge=0.0)
    extreme_tachycardia_max_bpm: float = Field(190.0, le=250.0)
    hypoxia_critical_spo2: float = Field(85.0, ge=50.0, le=100.0)
    hypothermia_min_temp: float = Field(32.0, ge=20.0)
    hyperthermia_max_temp: float = Field(41.0, le=45.0)

class UserHealthProfile(BaseModel):
    user_id: str = Field(..., min_length=2, max_length=64)
    full_name: str = Field(..., min_length=2, max_length=128)
    associated_wearable_ids: List[str] = Field(default_factory=list)
    emergency_contacts: List[EmergencyContact] = Field(default_factory=list)
    thresholds: EmergencyVitalsThresholds = Field(default_factory=EmergencyVitalsThresholds)
    auto_connect_on_approach: bool = True
    home_broadcast_enabled: bool = True

class EmergencyEventLog(BaseModel):
    event_id: str
    user_id: str
    timestamp: float
    iso_timestamp: str
    severity: EmergencySeverity
    trigger_reason: str
    vitals_snapshot: Dict[str, Any]
    contacts_notified: List[str]
    devices_broadcasted: List[str]
    resolved: bool = False
