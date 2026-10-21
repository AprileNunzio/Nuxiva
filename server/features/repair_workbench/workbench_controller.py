from typing import Annotated, Any, Dict, List

from fastapi import APIRouter, Depends, Path, Query

from server.features.repair_workbench.collaboration_service import WorkbenchCollaboration
from server.features.repair_workbench.launch_queue import workbench_launch_queue
from server.features.repair_workbench.ollama_vision import OllamaVisionAnalyzer
from server.features.repair_workbench.session_requests import (
    AnalyzeFrameRequest,
    ChatRequest,
    EscalationRequest,
    StartSessionRequest,
    TeachComponentRequest,
)
from server.features.repair_workbench.session_store import EncryptedSessionStore
from server.features.repair_workbench.workbench_service import WorkbenchService

IDENTIFIER_PATTERN = r"^[A-Za-z0-9_\-][A-Za-z0-9_.\-]{0,63}$"

workbench_router = APIRouter(prefix="/repair-workbench")
workbench_service = WorkbenchService(EncryptedSessionStore(), OllamaVisionAnalyzer())
workbench_collaboration = WorkbenchCollaboration(workbench_service)

SessionId = Annotated[str, Path(pattern=IDENTIFIER_PATTERN)]


def current_owner(
    user_id: Annotated[str, Query(pattern=IDENTIFIER_PATTERN)] = "user_primary",
) -> str:
    return user_id


Owner = Annotated[str, Depends(current_owner)]


def _public(session) -> Dict[str, Any]:
    return session.model_dump(mode="json", exclude={"owner_id"})


@workbench_router.post("/sessions")
async def start_session(payload: StartSessionRequest, owner: Owner) -> Dict[str, Any]:
    return {"status": "success", "session": _public(workbench_service.start(owner, payload))}


@workbench_router.get("/sessions/{session_id}")
async def get_session(session_id: SessionId, owner: Owner) -> Dict[str, Any]:
    return {"status": "success", "session": _public(workbench_service.get(owner, session_id))}


@workbench_router.post("/sessions/{session_id}/analyze-frame")
async def analyze_frame(
    session_id: SessionId, payload: AnalyzeFrameRequest, owner: Owner
) -> Dict[str, Any]:
    session, analyzed = await workbench_service.analyze(owner, session_id, payload)
    return {"status": "success", "analyzed": analyzed, "session": _public(session)}


@workbench_router.post("/sessions/{session_id}/teach-component")
async def teach_component(
    session_id: SessionId, payload: TeachComponentRequest, owner: Owner
) -> Dict[str, Any]:
    return {"status": "success", "session": _public(workbench_service.teach(owner, session_id, payload))}


@workbench_router.post("/sessions/{session_id}/chat")
async def chat(session_id: SessionId, payload: ChatRequest, owner: Owner) -> Dict[str, Any]:
    result = await workbench_collaboration.chat(owner, session_id, payload)
    return {"status": "success", **result}


@workbench_router.post("/sessions/{session_id}/escalate")
async def escalate(
    session_id: SessionId, payload: EscalationRequest, owner: Owner
) -> Dict[str, Any]:
    return {"status": "success", "result": workbench_collaboration.escalate(owner, session_id, payload)}


@workbench_router.get("/launch-requests")
async def launch_requests(
    owner: Owner, since: Annotated[float, Query(ge=0)] = 0.0
) -> Dict[str, Any]:
    pending: List[Dict[str, Any]] = [
        {"launch_id": r.launch_id, "project_id": r.project_id, "created_at": r.created_at}
        for r in workbench_launch_queue.pending(owner, since)
    ]
    return {"status": "success", "requests": pending}
