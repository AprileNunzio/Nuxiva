import asyncio
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict, Field

from server.config.env import settings
from server.core.plasticity import distillation
from server.core.plasticity.composition import plasticity_ledger, plasticity_service

router = APIRouter(prefix="/api/v1/cognition/plasticity", tags=["Nuxiva Plasticity"])

DATASET = Path("cortex") / "distillation.jsonl"
ADAPTER = Path("cortex") / "adapter"


class FeedbackRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    neuron_id: str = Field(min_length=3, max_length=64, pattern=r"^[a-z][a-z0-9_.-]{2,63}$")
    utterance: str = Field(min_length=1, max_length=500)
    outcome: str = Field(pattern=r"^(success|failure|corrected)$")
    corrected_to: Optional[str] = Field(default=None, min_length=3, max_length=64, pattern=r"^[a-z][a-z0-9_.-]{2,63}$")


class TrainRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    base_model: str = Field(min_length=3, max_length=200, pattern=r"^[A-Za-z0-9_.\-/]+$")
    epochs: int = Field(default=2, ge=1, le=10)


def _unwrap(result):
    if not result.is_ok:
        raise result.error
    return result.value


@router.get("/status")
async def status() -> Dict[str, Any]:
    missing = distillation.missing_dependencies()
    return {"ledger": _unwrap(await asyncio.to_thread(plasticity_service().status)),
            "distillation": {"available": not missing and distillation.gpu_available(), "missing": missing}}


@router.post("/feedback")
async def feedback(body: FeedbackRequest) -> Dict[str, Any]:
    return _unwrap(await asyncio.to_thread(
        plasticity_service().feedback, body.neuron_id, body.utterance, body.outcome, body.corrected_to))


@router.post("/consolidate")
async def consolidate() -> Dict[str, Any]:
    return _unwrap(await asyncio.to_thread(plasticity_service().consolidate))


@router.post("/distillation/dataset")
async def build_dataset() -> Dict[str, Any]:
    target = Path(settings.DATA_DIR) / DATASET
    count = _unwrap(await asyncio.to_thread(distillation.build_dataset, plasticity_ledger(), target))
    return {"examples": count, "path": str(target)}


@router.post("/distillation/train")
async def train(body: TrainRequest) -> Dict[str, Any]:
    return _unwrap(await asyncio.to_thread(
        distillation.train, Path(settings.DATA_DIR) / DATASET, body.base_model, Path(settings.DATA_DIR) / ADAPTER, body.epochs))
