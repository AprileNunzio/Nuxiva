from enum import Enum
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
import time

class MoodState(str, Enum):
    OPTIMAL_BALANCED = "optimal_balanced"
    DEPRESSED_DYSPHORIC = "depressed_dysphoric"
    ANXIOUS_STRESSED = "anxious_stressed"
    FATIGUED_BURNOUT = "fatigued_burnout"
    EUPHORIC_HIGH_ENERGY = "euphoric_high_energy"

class VocalDeliveryMode(str, Enum):
    WHISPER = "whisper"
    SOFT_INTIMATE = "soft_intimate"
    CALM_NATURAL = "calm_natural"
    ANIMATED_EXCITED = "animated_excited"
    TENSE_URGENT = "tense_urgent"
    SHOUTING = "shouting"
    FATIGUED_SLOW = "fatigued_slow"
    FLAT_MONOTONE = "flat_monotone"

class HeartRateMetrics(BaseModel):
    bpm: float = Field(..., ge=30.0, le=240.0)
    hrv_rmssd_ms: float = Field(..., ge=0.0)
    signal_quality: float = Field(..., ge=0.0, le=1.0)
    pulse_confidence: float = Field(..., ge=0.0, le=1.0)
    timestamp: float = Field(default_factory=time.time)

class VoiceAcousticBiomarkers(BaseModel):
    pitch_f0_mean_hz: float = Field(..., ge=40.0, le=600.0)
    pitch_variability_st: float = Field(..., ge=0.0)
    jitter_percent: float = Field(..., ge=0.0)
    shimmer_percent: float = Field(..., ge=0.0)
    monotone_score: float = Field(..., ge=0.0, le=1.0)
    vocal_energy_rms: float = Field(..., ge=0.0)
    speech_pause_ratio: float = Field(..., ge=0.0, le=1.0)
    depressive_vocal_indicator: float = Field(..., ge=0.0, le=1.0)
    whisper_probability: float = Field(0.0, ge=0.0, le=1.0)
    harmonic_to_noise_ratio_db: float = Field(12.0)
    high_freq_energy_ratio: float = Field(0.25, ge=0.0, le=1.0)
    zero_crossing_rate: float = Field(0.08, ge=0.0, le=1.0)
    speech_rate_sps: float = Field(3.5, ge=0.0)
    voicing_strength: float = Field(0.7, ge=0.0, le=1.0)
    delivery_mode: VocalDeliveryMode = VocalDeliveryMode.CALM_NATURAL

class OcularGazeBiomarkers(BaseModel):
    gaze_direction: str = Field("center")
    downward_gaze_ratio: float = Field(..., ge=0.0, le=1.0)
    blink_rate_per_min: float = Field(..., ge=0.0)
    eye_aspect_ratio_mean: float = Field(..., ge=0.0)
    fixation_stagnation_score: float = Field(..., ge=0.0, le=1.0)
    blunted_affect_indicator: float = Field(..., ge=0.0, le=1.0)

class PhysiologicalMultimodalPayload(BaseModel):
    user_id: str = Field(..., min_length=2, max_length=64)
    timestamp: float = Field(default_factory=time.time)
    heart_metrics: HeartRateMetrics
    vocal_metrics: VoiceAcousticBiomarkers
    ocular_metrics: OcularGazeBiomarkers

class VoiceAudioAnalysisPayload(BaseModel):
    user_id: str = Field(..., min_length=2, max_length=64)
    sample_rate: int = Field(16000, ge=8000, le=48000)
    pcm16_b64: Optional[str] = None
    samples: Optional[List[float]] = None
    timestamp: float = Field(default_factory=time.time)

class AffectiveInferenceResult(BaseModel):
    assessment_id: str
    user_id: str
    timestamp: float
    iso_timestamp: str
    detected_mood: MoodState
    vocal_delivery_mode: VocalDeliveryMode = VocalDeliveryMode.CALM_NATURAL
    whisper_probability: float = Field(0.0, ge=0.0, le=1.0)
    valence_score: float = Field(0.5, ge=0.0, le=1.0)
    arousal_score: float = Field(0.5, ge=0.0, le=1.0)
    depression_risk_score: float = Field(..., ge=0.0, le=1.0)
    anxiety_stress_score: float = Field(..., ge=0.0, le=1.0)
    fatigue_burnout_score: float = Field(..., ge=0.0, le=1.0)
    confidence: float = Field(..., ge=0.0, le=1.0)
    intervention_strategy_id: str
    system_prompt_adaptation: str
    voice_tone_guidance: Dict[str, Any]
    ambient_automation_triggers: List[Dict[str, Any]]
