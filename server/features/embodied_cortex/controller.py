import asyncio
from typing import Any, Dict

from fastapi import APIRouter

from server.features.embodied_cortex.schemas import (
    ActiveInferenceStepRequest,
    ConsolidateShortcutRequest,
    QuadraticSolveRequest,
)
from server.features.embodied_cortex.service import embodied_cortex_service

router = APIRouter(tags=["Nuxiva Neuro-Symbolic Cortical Columns & Embodied Cognition"])


def _unwrap(result: Any) -> Dict[str, Any]:
    if not result.is_ok:
        raise result.error
    return result.value


@router.get("/cognitive/embodied-cortex/overview")
async def get_embodied_cortex_overview() -> Dict[str, Any]:
    return _unwrap(await asyncio.to_thread(embodied_cortex_service().overview))


@router.post("/cognitive/embodied-cortex/columns/solve")
async def post_cortical_column_solve(req: QuadraticSolveRequest) -> Dict[str, Any]:
    return _unwrap(await asyncio.to_thread(embodied_cortex_service().solve_quadratic, req))


@router.post("/cognitive/embodied-cortex/columns/consolidate")
async def post_consolidate_shortcut(req: ConsolidateShortcutRequest) -> Dict[str, Any]:
    return _unwrap(await asyncio.to_thread(embodied_cortex_service().consolidate_shortcut, req))


@router.post("/cognitive/embodied-cortex/humanoid/step")
async def post_humanoid_active_inference_step(req: ActiveInferenceStepRequest) -> Dict[str, Any]:
    return _unwrap(await asyncio.to_thread(embodied_cortex_service().step_active_inference, req))
