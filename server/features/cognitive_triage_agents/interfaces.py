from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Any, Optional

class EmotionalState(str, Enum):
    CALM = "calm"
    ANXIOUS = "anxious"
    DEPRESSED = "depressed"
    FRUSTRATED = "frustrated"
    OVERWHELMED = "overwhelmed"

class RiskLevel(str, Enum):
    SAFE = "safe"
    ELEVATED = "elevated"
    SEVERE = "severe"
    CRITICAL_EMERGENCY = "critical_emergency"

class TriageMode(str, Enum):
    TRANSPARENT_COPROCESSOR = "transparent_coprocessor"
    ADAPTIVE_TONE = "adaptive_tone"
    ON_DEMAND_COACHING = "on_demand_coaching"
    SAFETY_INTERLOCK = "safety_interlock"

@dataclass
class UserCognitiveInput:
    user_id: str
    raw_text: str
    vocal_pitch_hz: float = 140.0
    vocal_jitter: float = 0.02
    hrv_ms: float = 45.0
    heart_rate_bpm: float = 72.0
    facial_valence: float = 0.0
    gaze_stability: float = 0.8
    session_context: Dict[str, Any] = field(default_factory=dict)

@dataclass
class PsychologicalEvaluation:
    emotional_state: EmotionalState
    empathy_depth: float
    cognitive_distortion: str
    deescalation_strategy: str
    supportive_reframing: str

@dataclass
class MethodologicalEvaluation:
    task_complexity: float
    overload_index: float
    socratic_steps: List[str]
    pragmatic_action_plan: List[str]
    cognitive_scaffolding: str

@dataclass
class PsychiatricSafetyEvaluation:
    risk_level: RiskLevel
    red_flags: List[str]
    requires_interlock: bool
    emergency_helpline_payload: Dict[str, str]
    emergency_dispatch_required: bool

@dataclass
class TriageConsensusResult:
    mode: TriageMode
    meta_prompt_directive: str
    speech_rate_factor: float
    tts_pitch_shift: float
    emotional_valence: float
    response_override: Optional[str]
    emergency_alert_triggered: bool
    psychological_summary: Dict[str, Any]
    methodological_summary: Dict[str, Any]
    psychiatric_summary: Dict[str, Any]
