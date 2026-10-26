from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from server.features.llm_gateway.ternary_engine import ternary_engine

ternary_router = APIRouter()

class TernaryActivationPayload(BaseModel):
    model_id: str

@ternary_router.get("/system/ternary-models")
async def list_ternary_models():
    models = ternary_engine.list_available_models()
    active_id = ternary_engine.get_active_model()
    return {
        "status": "success",
        "active_model": active_id,
        "models": [m.model_dump() for m in models],
        "active_savings": ternary_engine.calculate_memory_savings(active_id),
    }

@ternary_router.post("/system/ternary-models/activate")
async def activate_ternary_model(payload: TernaryActivationPayload):
    result = await ternary_engine.activate_single_model(payload.model_id)
    if result.get("status") == "error":
        raise HTTPException(status_code=400, detail=result.get("message"))
    return result
