from fastapi import APIRouter, Query
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional
from .interfaces import UserCognitiveInput
from .triage_service import cognitive_triage_service

cognitive_triage_router = APIRouter(prefix="/cognitive-triage", tags=["Cognitive Triage Agents"])

class CognitiveEvaluationRequest(BaseModel):
    user_id: str = Field(..., min_length=1, max_length=128)
    raw_text: str = Field(..., max_length=4096)
    vocal_pitch_hz: float = Field(140.0, ge=40.0, le=600.0)
    vocal_jitter: float = Field(0.02, ge=0.0, le=1.0)
    hrv_ms: float = Field(45.0, ge=5.0, le=300.0)
    heart_rate_bpm: float = Field(72.0, ge=30.0, le=240.0)
    facial_valence: float = Field(0.0, ge=-1.0, le=1.0)
    gaze_stability: float = Field(0.8, ge=0.0, le=1.0)
    session_context: Optional[Dict[str, Any]] = None

class ToggleServiceRequest(BaseModel):
    enabled: bool

@cognitive_triage_router.post("/evaluate")
async def evaluate_cognitive_input(req: CognitiveEvaluationRequest) -> Dict[str, Any]:
    sanitized_text = req.raw_text.strip()
    user_input = UserCognitiveInput(
        user_id=req.user_id,
        raw_text=sanitized_text,
        vocal_pitch_hz=req.vocal_pitch_hz,
        vocal_jitter=req.vocal_jitter,
        hrv_ms=req.hrv_ms,
        heart_rate_bpm=req.heart_rate_bpm,
        facial_valence=req.facial_valence,
        gaze_stability=req.gaze_stability,
        session_context=req.session_context or {}
    )
    result = await cognitive_triage_service.evaluate_input(user_input)
    return {
        "status": "success",
        "mode": result.mode.value,
        "meta_prompt_directive": result.meta_prompt_directive,
        "speech_rate_factor": result.speech_rate_factor,
        "tts_pitch_shift": result.tts_pitch_shift,
        "emotional_valence": result.emotional_valence,
        "response_override": result.response_override,
        "emergency_alert_triggered": result.emergency_alert_triggered,
        "psychological_summary": result.psychological_summary,
        "methodological_summary": result.methodological_summary,
        "psychiatric_summary": result.psychiatric_summary
    }

@cognitive_triage_router.get("/status")
async def get_triage_status() -> Dict[str, Any]:
    return await cognitive_triage_service.get_status()

@cognitive_triage_router.get("/history")
async def get_triage_history(limit: int = Query(20, ge=1, le=50)) -> Dict[str, Any]:
    items = await cognitive_triage_service.get_history(limit)
    return {"status": "success", "count": len(items), "history": items}

@cognitive_triage_router.post("/toggle")
async def toggle_service(req: ToggleServiceRequest) -> Dict[str, Any]:
    cognitive_triage_service.set_enabled(req.enabled)
    return {"status": "success", "enabled": req.enabled}
