from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ModelPriority(int, Enum):
    BACKGROUND = 10
    STANDBY = 20
    ACTIVE_INTERACTION = 50
    EMERGENCY_REALTIME = 90


class ModelKind(str, Enum):
    WAKEPUSH = "wakepush"
    WHISPER = "whisper"
    FAST_LLM = "fast_llm"
    DEEP_BRAIN = "deep_brain"
    VISION = "vision"
    TTS = "tts"


@dataclass(frozen=True)
class ModelAllocation:
    kind: ModelKind
    vram_mb: int
    ram_mb: int
    priority: ModelPriority
    loaded: bool = False

    def can_coexist_with(self, total_vram_limit_mb: int, current_allocated_mb: int) -> bool:
        if self.vram_mb == 0:
            return True
        return (current_allocated_mb + self.vram_mb) <= total_vram_limit_mb
