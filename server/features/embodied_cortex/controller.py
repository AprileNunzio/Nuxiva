import asyncio
from typing import Any, Dict, List

from fastapi import APIRouter

from server.features.embodied_cortex.schemas import (
    ActiveInferenceStepRequest,
    ConsolidateShortcutRequest,
    FieldbusTransitionRequest,
    InitiateConfrontationRequest,
    QuadraticSolveRequest,
    ResolveConfrontationRequest,
    SynthesizeFormalismRequest,
)
from server.features.embodied_cortex.service import embodied_cortex_service

router = APIRouter(tags=["Nuxiva Neuro-Symbolic Cortical Columns & Embodied Cognition"])


def _unwrap(result: Any) -> Any:
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


@router.post("/cognitive/embodied-cortex/confrontation/initiate")
async def post_initiate_confrontation(req: InitiateConfrontationRequest) -> Dict[str, Any]:
    return _unwrap(await asyncio.to_thread(embodied_cortex_service().initiate_confrontation, req))


@router.post("/cognitive/embodied-cortex/confrontation/resolve")
async def post_resolve_confrontation(req: ResolveConfrontationRequest) -> Dict[str, Any]:
    return _unwrap(await asyncio.to_thread(embodied_cortex_service().resolve_confrontation, req))


@router.get("/cognitive/embodied-cortex/confrontation/pending")
async def get_pending_confrontations() -> List[Dict[str, Any]]:
    return _unwrap(await asyncio.to_thread(embodied_cortex_service().list_pending_confrontations))


@router.get("/cognitive/embodied-cortex/confrontation/resolved")
async def get_resolved_confrontations() -> List[Dict[str, Any]]:
    return _unwrap(await asyncio.to_thread(embodied_cortex_service().list_resolved_confrontations))


@router.post("/cognitive/embodied-cortex/ontology/synthesize")
async def post_synthesize_formalism(req: SynthesizeFormalismRequest) -> Dict[str, Any]:
    return _unwrap(await asyncio.to_thread(embodied_cortex_service().synthesize_formalism, req))


@router.get("/cognitive/embodied-cortex/ontology/formalisms")
async def get_invented_formalisms() -> List[Dict[str, Any]]:
    return _unwrap(await asyncio.to_thread(embodied_cortex_service().list_formalisms))


@router.get("/cognitive/embodied-cortex/humanoid/joints34")
async def get_humanoid_joints34() -> List[Dict[str, Any]]:
    return _unwrap(await asyncio.to_thread(embodied_cortex_service().list_joints34))


@router.post("/cognitive/embodied-cortex/fieldbus/transition")
async def post_fieldbus_transition(req: FieldbusTransitionRequest) -> Dict[str, Any]:
    return _unwrap(await asyncio.to_thread(embodied_cortex_service().fieldbus_transition, req))
