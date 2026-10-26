from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, List, Optional

logger = logging.getLogger("nuxiva.spatial_webos")

try:
    from nuxiva_native import RustIntentRouter, RustSpatialArbiter

    HAS_NATIVE_RUST = True
except ImportError:
    HAS_NATIVE_RUST = False


class AssistantMorphology(str, Enum):
    CORE_HERO = "CORE_HERO"
    FLOATING_ORB = "FLOATING_ORB"
    AMBIENT_STREAM = "AMBIENT_STREAM"
    WHISPER_PILL = "WHISPER_PILL"


class NotificationPriority(str, Enum):
    P0_CRITICAL = "P0_CRITICAL"
    P1_HIGH = "P1_HIGH"
    P2_NORMAL = "P2_NORMAL"
    P3_LOW = "P3_LOW"


class ViewportMode(str, Enum):
    IMMERSIVE_STAGE = "IMMERSIVE_STAGE"
    SPLIT_PIVOT = "SPLIT_PIVOT"
    FLOATING_WIDGET = "FLOATING_WIDGET"
    AMBIENT_BACKGROUND = "AMBIENT_BACKGROUND"


class GpuLoad(str, Enum):
    NONE = "NONE"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    EXTREME = "EXTREME"


class SafeZone(str, Enum):
    TOP_LEFT = "TOP_LEFT"
    TOP_RIGHT = "TOP_RIGHT"
    BOTTOM_LEFT = "BOTTOM_LEFT"
    BOTTOM_RIGHT = "BOTTOM_RIGHT"
    CENTER = "CENTER"
    SCREEN_EDGE_GLOW = "SCREEN_EDGE_GLOW"


class VoiceInteraction(str, Enum):
    CONTINUOUS_CO_PILOT = "CONTINUOUS_CO_PILOT"
    ON_DEMAND_ASSISTANT = "ON_DEMAND_ASSISTANT"
    SILENT_OBSERVER = "SILENT_OBSERVER"


class FocusLockLevel(int, Enum):
    LOCK_0_IDLE = 0
    LOCK_1_FOCUS = 1
    LOCK_2_ENGAGED = 2
    LOCK_3_IMMERSIVE = 3


class ArbitrationAction(str, Enum):
    PREEMPTION_TOTAL = "PREEMPTION_TOTAL"
    SMART_PIP = "SMART_PIP"
    VOICE_INTERJECT = "VOICE_INTERJECT"
    MICRO_BADGE = "MICRO_BADGE"
    DEFERRAL = "DEFERRAL"
    SILENT_LOG = "SILENT_LOG"


@dataclass
class AssistantRequirement:
    preferred_morphology: AssistantMorphology
    fallback_morphology: AssistantMorphology
    allowed_safe_zones: List[SafeZone] = field(default_factory=list)
    voice_interaction: VoiceInteraction = VoiceInteraction.CONTINUOUS_CO_PILOT


@dataclass
class ContextManifest:
    context_id: str
    viewport_mode: ViewportMode
    gpu_load: GpuLoad
    assistant_requirement: AssistantRequirement
    focus_lock_level: FocusLockLevel

    @classmethod
    def idle_default(cls) -> ContextManifest:
        return cls(
            context_id="app.nuxiva.idle",
            viewport_mode=ViewportMode.AMBIENT_BACKGROUND,
            gpu_load=GpuLoad.LOW,
            assistant_requirement=AssistantRequirement(
                preferred_morphology=AssistantMorphology.CORE_HERO,
                fallback_morphology=AssistantMorphology.FLOATING_ORB,
                allowed_safe_zones=[SafeZone.CENTER],
                voice_interaction=VoiceInteraction.CONTINUOUS_CO_PILOT,
            ),
            focus_lock_level=FocusLockLevel.LOCK_0_IDLE,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "context_id": self.context_id,
            "viewport_mode": self.viewport_mode.value,
            "gpu_load": self.gpu_load.value,
            "assistant_requirement": {
                "preferred_morphology": self.assistant_requirement.preferred_morphology.value,
                "fallback_morphology": self.assistant_requirement.fallback_morphology.value,
                "allowed_safe_zones": [z.value for z in self.assistant_requirement.allowed_safe_zones],
                "voice_interaction": self.assistant_requirement.voice_interaction.value,
            },
            "focus_lock_level": self.focus_lock_level.value,
        }


@dataclass
class NotificationEvent:
    id: str
    priority: NotificationPriority
    title_key: str
    message_key: str
    source_module: str
    timestamp_ms: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "priority": self.priority.value,
            "title_key": self.title_key,
            "message_key": self.message_key,
            "source_module": self.source_module,
            "timestamp_ms": self.timestamp_ms,
        }


@dataclass
class ArbitrationResult:
    action: ArbitrationAction
    target_morphology: AssistantMorphology
    assigned_safe_zone: Optional[SafeZone]
    suspend_primary_stage: bool
    target_layer: str
    should_defer: bool
    reason_code: str


class SpatialWebOSEngine:
    def __init__(self) -> None:
        self.use_rust = HAS_NATIVE_RUST
        self._deferred_events: list[NotificationEvent] = []
        if self.use_rust:
            self._rust_arbiter = RustSpatialArbiter()
            self._rust_router = RustIntentRouter()

    def arbitrate(self, event: NotificationEvent, manifest: ContextManifest) -> ArbitrationResult:
        if self.use_rust:
            res_str = self._rust_arbiter.arbitrate_json(json.dumps(event.to_dict()), json.dumps(manifest.to_dict()))
            raw = json.loads(res_str)
            safe_zone = SafeZone(raw["assigned_safe_zone"]) if raw.get("assigned_safe_zone") else None
            return ArbitrationResult(
                action=ArbitrationAction(raw["action"]),
                target_morphology=AssistantMorphology(raw["target_morphology"]),
                assigned_safe_zone=safe_zone,
                suspend_primary_stage=bool(raw["suspend_primary_stage"]),
                target_layer=str(raw["target_layer"]),
                should_defer=bool(raw["should_defer"]),
                reason_code=str(raw["reason_code"]),
            )

        lock = manifest.focus_lock_level
        preferred = manifest.assistant_requirement.preferred_morphology
        fallback = manifest.assistant_requirement.fallback_morphology
        safe_zones = manifest.assistant_requirement.allowed_safe_zones

        if event.priority == NotificationPriority.P0_CRITICAL:
            return ArbitrationResult(
                action=ArbitrationAction.PREEMPTION_TOTAL,
                target_morphology=AssistantMorphology.CORE_HERO,
                assigned_safe_zone=None,
                suspend_primary_stage=True,
                target_layer="Z4CriticalInterrupt",
                should_defer=False,
                reason_code="p0_preemption",
            )

        if event.priority == NotificationPriority.P1_HIGH:
            if lock == FocusLockLevel.LOCK_3_IMMERSIVE:
                return ArbitrationResult(
                    action=ArbitrationAction.VOICE_INTERJECT,
                    target_morphology=AssistantMorphology.AMBIENT_STREAM,
                    assigned_safe_zone=None,
                    suspend_primary_stage=False,
                    target_layer="Z3Assistant",
                    should_defer=False,
                    reason_code="p1_voice_interject",
                )
            zone = safe_zones[0] if safe_zones else SafeZone.TOP_RIGHT
            return ArbitrationResult(
                action=ArbitrationAction.SMART_PIP,
                target_morphology=preferred,
                assigned_safe_zone=zone,
                suspend_primary_stage=False,
                target_layer="Z2ContextualHud",
                should_defer=False,
                reason_code="p1_smart_pip",
            )

        if event.priority == NotificationPriority.P2_NORMAL:
            if lock == FocusLockLevel.LOCK_0_IDLE:
                return ArbitrationResult(
                    action=ArbitrationAction.SMART_PIP,
                    target_morphology=AssistantMorphology.CORE_HERO,
                    assigned_safe_zone=SafeZone.CENTER,
                    suspend_primary_stage=False,
                    target_layer="Z2ContextualHud",
                    should_defer=False,
                    reason_code="p2_immediate",
                )
            if lock == FocusLockLevel.LOCK_1_FOCUS:
                zone = safe_zones[0] if safe_zones else SafeZone.BOTTOM_RIGHT
                return ArbitrationResult(
                    action=ArbitrationAction.MICRO_BADGE,
                    target_morphology=preferred,
                    assigned_safe_zone=zone,
                    suspend_primary_stage=False,
                    target_layer="Z2ContextualHud",
                    should_defer=False,
                    reason_code="p2_micro_badge",
                )
            self._deferred_events.append(event)
            return ArbitrationResult(
                action=ArbitrationAction.DEFERRAL,
                target_morphology=fallback if lock == FocusLockLevel.LOCK_3_IMMERSIVE else preferred,
                assigned_safe_zone=None,
                suspend_primary_stage=False,
                target_layer="Z1PrimaryStage",
                should_defer=True,
                reason_code="p2_deferred",
            )

        return ArbitrationResult(
            action=ArbitrationAction.SILENT_LOG,
            target_morphology=preferred,
            assigned_safe_zone=None,
            suspend_primary_stage=False,
            target_layer="Z0Ambient",
            should_defer=False,
            reason_code="p3_silent",
        )

    def resolve_intent(self, text: str) -> Optional[str]:
        if self.use_rust:
            return self._rust_router.resolve_intent(text)

        t = text.lower()
        if "chess" in t or "scacchi" in t:
            return "app.nuxiva.chess"
        if "3d" in t or "cad" in t:
            return "app.nuxiva.cad3d"
        if "whisper" in t or "silent" in t:
            return "app.nuxiva.whisper"
        if "idle" in t or "home" in t:
            return "app.nuxiva.idle"
        return None

    def drain_deferred(self) -> list[NotificationEvent]:
        if self.use_rust:
            raw = self._rust_arbiter.drain_deferred_json()
            items = json.loads(raw)
            return [
                NotificationEvent(
                    id=x["id"],
                    priority=NotificationPriority(x["priority"]),
                    title_key=x["title_key"],
                    message_key=x["message_key"],
                    source_module=x["source_module"],
                    timestamp_ms=int(x["timestamp_ms"]),
                )
                for x in items
            ]
        items = list(self._deferred_events)
        self._deferred_events.clear()
        return items
