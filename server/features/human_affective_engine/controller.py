from fastapi import APIRouter, HTTPException
from typing import Dict, Any, Optional
from server.features.human_affective_engine.interfaces import (
    PhysiologicalMultimodalPayload,
    AffectiveInferenceResult,
)
from server.features.human_affective_engine.affective_service import human_affective_service

affective_router = APIRouter(prefix="/affective", tags=["human_affective_engine"])

@affective_router.post("/evaluate", response_model=AffectiveInferenceResult)
async def evaluate_affective_state(payload: PhysiologicalMultimodalPayload) -> AffectiveInferenceResult:
    return await human_affective_service.process_multimodal_assessment(payload)

@affective_router.get("/user/{user_id}/status", response_model=Optional[AffectiveInferenceResult])
async def get_user_mood_status(user_id: str) -> Optional[AffectiveInferenceResult]:
    res = human_affective_service.get_latest_user_affect(user_id)
    if not res:
        raise HTTPException(status_code=404, detail="Nessuna valutazione emotiva registrata per questo utente.")
    return res

@affective_router.get("/metrics")
async def get_affective_engine_metrics() -> Dict[str, Any]:
    return human_affective_service.get_service_metrics()
