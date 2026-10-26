from typing import Any, Dict
from fastapi import APIRouter
from server.features.cognitive_arbiter.schemas import (
    BenchmarkSuiteRequest,
    CascadeDecisionRequest,
    CommitteeDecisionRequest,
    ThresholdTuneRequest,
    TypedDecisionRequest,
)
from server.features.cognitive_arbiter.service import cognitive_arbiter_service

router = APIRouter(tags=["Nuxiva Cognitive Decision & Calibration Lab"])


@router.get("/api/v1/decision-lab/overview")
@router.get("/api/brains/decision-lab")
@router.get("/api/v2/brain/decision-lab")
async def get_decision_lab_overview() -> Dict[str, Any]:
    return cognitive_arbiter_service.get_overview()


@router.post("/api/v1/decision-lab/decide")
@router.post("/api/brains/decision-lab/decide")
@router.post("/api/v2/brain/decision-lab/decide")
async def post_typed_decision(req: TypedDecisionRequest) -> Dict[str, Any]:
    return cognitive_arbiter_service.execute_typed_decision(req)


@router.post("/api/v1/decision-lab/cascade")
@router.post("/api/brains/decision-lab/cascade")
@router.post("/api/v2/brain/decision-lab/cascade")
async def post_cascade_decision(req: CascadeDecisionRequest) -> Dict[str, Any]:
    return cognitive_arbiter_service.execute_cascade(req)


@router.post("/api/v1/decision-lab/committee")
@router.post("/api/brains/decision-lab/committee")
@router.post("/api/v2/brain/decision-lab/committee")
async def post_committee_decision(req: CommitteeDecisionRequest) -> Dict[str, Any]:
    return cognitive_arbiter_service.execute_committee(req)


@router.post("/api/v1/decision-lab/benchmark")
@router.post("/api/brains/decision-lab/benchmark")
@router.post("/api/v2/brain/decision-lab/benchmark")
async def post_benchmark_suite(req: BenchmarkSuiteRequest) -> Dict[str, Any]:
    return cognitive_arbiter_service.run_benchmark(req)


@router.post("/api/v1/decision-lab/conformance")
@router.post("/api/brains/decision-lab/conformance")
@router.post("/api/v2/brain/decision-lab/conformance")
async def post_conformance_check() -> Dict[str, Any]:
    return cognitive_arbiter_service.run_conformance()


@router.put("/api/v1/decision-lab/cascade/threshold")
@router.put("/api/brains/decision-lab/threshold")
@router.put("/api/v2/brain/decision-lab/threshold")
async def put_cascade_threshold(req: ThresholdTuneRequest) -> Dict[str, Any]:
    return cognitive_arbiter_service.update_threshold(req)
