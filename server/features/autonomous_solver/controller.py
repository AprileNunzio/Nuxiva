from typing import List
from fastapi import APIRouter, HTTPException

from server.features.autonomous_solver.models import (
    AutonomousSolveRequest,
    AutonomousSolveResult,
)
from server.features.autonomous_solver.solver_engine import universal_autonomous_solver

solver_router = APIRouter(prefix="/autonomous-solver", tags=["autonomous_solver"])


@solver_router.post("/solve", response_model=AutonomousSolveResult)
async def solve_autonomously(payload: AutonomousSolveRequest) -> AutonomousSolveResult:
    return await universal_autonomous_solver.solve(payload)


@solver_router.get("/jobs", response_model=List[AutonomousSolveResult])
async def list_solver_jobs() -> List[AutonomousSolveResult]:
    return universal_autonomous_solver.list_jobs()


@solver_router.get("/jobs/{job_id}", response_model=AutonomousSolveResult)
async def get_solver_job(job_id: str) -> AutonomousSolveResult:
    res = universal_autonomous_solver.get_job(job_id)
    if not res:
        raise HTTPException(status_code=404, detail="Job autonomo non trovato.")
    return res
