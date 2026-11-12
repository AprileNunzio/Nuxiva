import sys
from pathlib import Path
from typing import Any, Dict
from fastapi import APIRouter, HTTPException, Request
from state import store

_ROOT = str(Path(__file__).resolve().parents[4])
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from server.features.cognitive_arbiter.schemas import (
    BenchmarkSuiteRequest,
    CascadeDecisionRequest,
    CommitteeDecisionRequest,
    ThresholdTuneRequest,
    TypedDecisionRequest,
)
from server.features.cognitive_arbiter.service import cognitive_arbiter_service

admin_routes = APIRouter()
public_routes = APIRouter()


@admin_routes.get("/api/brains/decision-lab")
@admin_routes.get("/api/v2/brain/decision-lab")
@public_routes.get("/api/brains/decision-lab")
@public_routes.get("/api/v2/brain/decision-lab")
async def get_decision_lab() -> Dict[str, Any]:
    return cognitive_arbiter_service.get_overview()


@admin_routes.post("/api/brains/decision-lab/decide")
@admin_routes.post("/api/v2/brain/decision-lab/decide")
@public_routes.post("/api/brains/decision-lab/decide")
@public_routes.post("/api/v2/brain/decision-lab/decide")
async def post_typed_decide(request: Request) -> Dict[str, Any]:
    body = await request.json()
    if not isinstance(body, dict):
        raise HTTPException(400, "decision_lab.invalid_payload")
    req = TypedDecisionRequest(**body)
    return cognitive_arbiter_service.execute_typed_decision(req)


@admin_routes.post("/api/brains/decision-lab/cascade")
@admin_routes.post("/api/v2/brain/decision-lab/cascade")
@public_routes.post("/api/brains/decision-lab/cascade")
@public_routes.post("/api/v2/brain/decision-lab/cascade")
async def post_decision_cascade(request: Request) -> Dict[str, Any]:
    body = await request.json()
    if not isinstance(body, dict):
        raise HTTPException(400, "decision_lab.invalid_payload")
    req = CascadeDecisionRequest(**body)
    return cognitive_arbiter_service.execute_cascade(req)


@admin_routes.post("/api/brains/decision-lab/committee")
@admin_routes.post("/api/v2/brain/decision-lab/committee")
@public_routes.post("/api/brains/decision-lab/committee")
@public_routes.post("/api/v2/brain/decision-lab/committee")
async def post_decision_committee(request: Request) -> Dict[str, Any]:
    body = await request.json()
    if not isinstance(body, dict):
        raise HTTPException(400, "decision_lab.invalid_payload")
    req = CommitteeDecisionRequest(**body)
    return cognitive_arbiter_service.execute_committee(req)


@admin_routes.post("/api/brains/decision-lab/benchmark")
@admin_routes.post("/api/v2/brain/decision-lab/benchmark")
@public_routes.post("/api/brains/decision-lab/benchmark")
@public_routes.post("/api/v2/brain/decision-lab/benchmark")
async def post_decision_benchmark(request: Request) -> Dict[str, Any]:
    body = await request.json()
    if not isinstance(body, dict):
        raise HTTPException(400, "decision_lab.invalid_payload")
    req = BenchmarkSuiteRequest(**body)
    result = cognitive_arbiter_service.run_benchmark(req)
    store.event("INFO", f"decision_lab.benchmark_completed ({req.preset})", "brain")
    return result


@admin_routes.post("/api/brains/decision-lab/conformance")
@admin_routes.post("/api/v2/brain/decision-lab/conformance")
@public_routes.post("/api/brains/decision-lab/conformance")
@public_routes.post("/api/v2/brain/decision-lab/conformance")
async def post_decision_conformance() -> Dict[str, Any]:
    result = cognitive_arbiter_service.run_conformance()
    store.event("INFO", "decision_lab.conformance_checked", "brain")
    return result


@admin_routes.put("/api/brains/decision-lab/threshold")
@admin_routes.put("/api/v2/brain/decision-lab/threshold")
@public_routes.put("/api/brains/decision-lab/threshold")
@public_routes.put("/api/v2/brain/decision-lab/threshold")
async def put_decision_threshold(request: Request) -> Dict[str, Any]:
    body = await request.json()
    if not isinstance(body, dict):
        raise HTTPException(400, "decision_lab.invalid_payload")
    req = ThresholdTuneRequest(**body)
    result = cognitive_arbiter_service.update_threshold(req)
    store.event("INFO", f"decision_lab.threshold_updated: {req.threshold}", "brain")
    return result
