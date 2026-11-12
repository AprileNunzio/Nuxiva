from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class CapabilityScope(str, Enum):
    NETWORK_HTTP = "network:http"
    FILESYSTEM_READ = "fs:read"
    FILESYSTEM_WRITE = "fs:write"
    AUDIO_CAPTURE = "audio:capture"
    CAMERA_STREAM = "camera:stream"
    HARDWARE_GPIO = "hardware:gpio"


@dataclass(frozen=True)
class CapabilityGrant:
    scope: CapabilityScope
    target_pattern: str
    expires_at: float
    max_payload_bytes: int = 1_048_576

    def is_valid_at(self, current_time: float) -> bool:
        return current_time <= self.expires_at

    def allows(self, scope: CapabilityScope, resource: str, payload_size: int, current_time: float) -> bool:
        if not self.is_valid_at(current_time):
            return False
        if self.scope != scope:
            return False
        if payload_size > self.max_payload_bytes:
            return False
        if self.target_pattern == "*":
            return True
        return resource.startswith(self.target_pattern)
