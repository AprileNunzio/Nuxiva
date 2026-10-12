from enum import Enum
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
import time

class WearableProtocol(str, Enum):
    BLE_STANDARD = "ble_standard"
    GOOGLE_FITBIT = "google_fitbit"
    GOOGLE_FIT = "google_fit"
    RENPHO_SMART_SCALE = "renpho_smart_scale"
    ANT_PLUS = "ant_plus"
    COMPANION_REST = "companion_rest"

class ConnectionStatus(str, Enum):
    CONNECTED = "connected"
    CONNECTING = "connecting"
    DISCONNECTED = "disconnected"
    ERROR = "error"

class RealtimeVitalTelemetry(BaseModel):
    device_id: str = Field(..., min_length=2, max_length=64)
    device_name: str = Field(..., min_length=2, max_length=128)
    protocol: WearableProtocol
    timestamp: float = Field(default_factory=time.time)
    heart_rate_bpm: Optional[float] = Field(None, ge=0.0, le=250.0)
    spo2_percentage: Optional[float] = Field(None, ge=0.0, le=100.0)
    hrv_rmssd_ms: Optional[float] = Field(None, ge=0.0, le=300.0)
    skin_temperature_celsius: Optional[float] = Field(None, ge=20.0, le=45.0)
    electrodermal_activity_eda: Optional[float] = Field(None, ge=0.0)
    steps_today: Optional[int] = Field(None, ge=0)
    calories_burned_kcal: Optional[float] = Field(None, ge=0.0)
    respiratory_rate_rpm: Optional[float] = Field(None, ge=5.0, le=60.0)
    battery_level_percentage: Optional[int] = Field(None, ge=0, le=100)

class BodyCompositionData(BaseModel):
    device_id: str
    timestamp: float = Field(default_factory=time.time)
    weight_kg: float = Field(..., ge=20.0, le=300.0)
    bmi: float = Field(..., ge=10.0, le=60.0)
    body_fat_percentage: Optional[float] = Field(None, ge=3.0, le=60.0)
    muscle_mass_kg: Optional[float] = Field(None, ge=10.0, le=150.0)
    bone_mass_kg: Optional[float] = Field(None, ge=1.0, le=15.0)
    water_percentage: Optional[float] = Field(None, ge=20.0, le=80.0)
    visceral_fat_index: Optional[int] = Field(None, ge=1, le=30)
    metabolic_age_years: Optional[int] = Field(None, ge=10, le=120)

class WearableDeviceRegistration(BaseModel):
    device_id: str = Field(..., min_length=2, max_length=64, pattern=r"^[a-zA-Z0-9_\-:]+$")
    name: str = Field(..., min_length=2, max_length=128)
    protocol: WearableProtocol
    mac_address: Optional[str] = Field(None, pattern=r"^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$")
    auth_token: Optional[str] = None
    is_active: bool = True
    status: ConnectionStatus = ConnectionStatus.DISCONNECTED
    last_sync_timestamp: float = 0.0

class WearableSystemState(BaseModel):
    connected_devices_count: int
    devices: List[WearableDeviceRegistration]
    latest_vitals: Optional[RealtimeVitalTelemetry] = None
    latest_body_metrics: Optional[BodyCompositionData] = None
    multimodal_fusion_active: bool = True
