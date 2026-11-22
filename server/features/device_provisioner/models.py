from enum import Enum
from typing import Any, Dict, List, Optional
import time
from pydantic import BaseModel, Field


class DeviceType(str, Enum):
    ESP32 = "esp32"
    DEBIAN_SERVER = "debian_server"


class SerialPortCandidate(BaseModel):
    port: str
    description: str = ""
    hwid: str = ""
    vid: Optional[str] = None
    pid: Optional[str] = None
    chip_hint: str = "unknown"
    is_esp32_likely: bool = False


class ProvisionStepLog(BaseModel):
    step: str
    status: str  # "ok", "fallback", "skipped", "failed"
    detail: str
    duration_ms: float = 0.0


class Esp32ProvisionRequest(BaseModel):
    user_id: str = Field(..., min_length=1, max_length=64)
    port: Optional[str] = None
    wifi_vault_entry_id: Optional[str] = None
    wifi_ssid: str = ""
    wifi_password: str = ""
    nuxiva_server_url: str = "http://nuxiva.local:80"
    enrollment_token: str = ""
    board_env: str = "esp32dev"
    dry_run: bool = False


class DebianProbeRequest(BaseModel):
    user_id: str = Field(..., min_length=1, max_length=64)
    host: str = Field(..., min_length=1, max_length=255)
    port: int = Field(22, ge=1, le=65535)
    username: str = "root"
    ssh_vault_entry_id: Optional[str] = None
    ssh_password: str = ""
    ssh_key_path: str = ""


class DebianProvisionRequest(DebianProbeRequest):
    install_mode: str = Field("satellite", pattern="^(satellite|full_server)$")
    nuxiva_server_url: str = "http://nuxiva.local:80"
    dry_run: bool = False


class ProvisionJobResult(BaseModel):
    job_id: str
    device_type: DeviceType
    target: str
    success: bool
    detected_info: Dict[str, Any] = Field(default_factory=dict)
    steps: List[ProvisionStepLog] = Field(default_factory=list)
    summary: str
    timestamp: float = Field(default_factory=time.time)
