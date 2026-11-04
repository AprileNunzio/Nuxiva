from typing import List, Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from server.features.project_workspace.manager import project_manager
from server.features.project_workspace.chief_supervisor import chief_supervisor
from server.features.project_workspace.project_models import WarRoomMessage, WarRoomMessageType
from server.features.project_workspace.inter_agent_dialogue import post_inter_agent_message

project_router = APIRouter()

class CreateProjectPayload(BaseModel):
    name: str
    goal: str
    autonomous_247: bool = False
    custom_agents: List[Any] = []

class AgentActionPayload(BaseModel):
    agent_id: str

class WarRoomPostPayload(BaseModel):
    sender_id: str
    sender_name: str
    sender_role: str
    message_type: str = "user_input"
    content: str
    attachments: List[Any] = []

class AgentEscalatePayload(BaseModel):
    requester_agent_id: str
    specialty: str
    justification: str

class AgentRecruitPayload(BaseModel):
    requester_agent_id: str
    target_agent_id: str
    justification: str

@project_router.get("/projects")
async def list_projects(user_id: str = "user_primary"):
    return {"status": "success", "projects": [p.model_dump() for p in project_manager.get_all(user_id)]}

@project_router.post("/projects")
async def create_new_project(payload: CreateProjectPayload, user_id: str = "user_primary"):
    project = project_manager.create_project(
        user_id=user_id,
        name=payload.name,
        goal=payload.goal,
        autonomous_247=payload.autonomous_247,
        custom_agents=payload.custom_agents or None,
    )
    return {"status": "success", "project": project.model_dump()}

@project_router.get("/projects/{project_id}")
async def get_project_details(project_id: str, user_id: str = "user_primary"):
    project = project_manager.get_by_id(user_id, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Progetto non trovato")
    return {"status": "success", "project": project.model_dump()}

@project_router.post("/projects/{project_id}/agents/add")
async def add_agent_to_project(project_id: str, payload: AgentActionPayload, user_id: str = "user_primary"):
    ok = project_manager.add_agent_to_project(user_id, project_id, payload.agent_id)
    if not ok:
        raise HTTPException(status_code=400, detail="Impossibile aggiungere l'agente o gia presente")
    return {"status": "success", "agent_id": payload.agent_id}

@project_router.post("/projects/{project_id}/agents/remove")
async def remove_agent_from_project(project_id: str, payload: AgentActionPayload, user_id: str = "user_primary"):
    ok = project_manager.remove_agent_from_project(user_id, project_id, payload.agent_id)
    if not ok:
        raise HTTPException(status_code=400, detail="Impossibile rimuovere l'agente")
    return {"status": "success", "agent_id": payload.agent_id}

@project_router.get("/projects/{project_id}/war-room")
async def get_war_room_feed(project_id: str, user_id: str = "user_primary"):
    project = project_manager.get_by_id(user_id, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Progetto non trovato")
    return {
        "status": "success",
        "project_id": project_id,
        "feed": [m.model_dump() for m in project.war_room_feed],
    }

@project_router.post("/projects/{project_id}/war-room/message")
async def post_war_room_message(project_id: str, payload: WarRoomPostPayload, user_id: str = "user_primary"):
    try:
        msg_type = WarRoomMessageType(payload.message_type)
    except ValueError:
        msg_type = WarRoomMessageType.USER_INPUT

    msg = WarRoomMessage(
        sender_id=payload.sender_id,
        sender_name=payload.sender_name,
        sender_role=payload.sender_role,
        message_type=msg_type,
        content=payload.content,
        attachments=payload.attachments,
    )
    saved_msg = project_manager.post_war_room_message(user_id, project_id, msg)
    return {"status": "success", "message": saved_msg.model_dump()}

@project_router.get("/projects/{project_id}/analytics")
async def get_project_analytics(project_id: str, user_id: str = "user_primary"):
    project = project_manager.get_by_id(user_id, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Progetto non trovato")
    analytics = chief_supervisor.generate_war_room_analytics(project)
    return {"status": "success", "analytics": analytics}

@project_router.post("/projects/{project_id}/agents/recruit")
async def recruit_agent_to_project(project_id: str, payload: AgentRecruitPayload, user_id: str = "user_primary"):
    project = project_manager.get_by_id(user_id, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Progetto non trovato")
    result = chief_supervisor.request_agent_recruitment(
        project=project,
        requester_agent_id=payload.requester_agent_id,
        target_agent_id=payload.target_agent_id,
        justification=payload.justification,
    )
    project_manager.save(user_id, project)
    return {"status": "success", "result": result}

class AgentDialoguePayload(BaseModel):
    sender_id: str
    recipient_id: str
    content: str
    message_type: str = "thought"

@project_router.post("/projects/{project_id}/agents/dialogue")
async def post_inter_agent_dialogue(project_id: str, payload: AgentDialoguePayload, user_id: str = "user_primary"):
    project = project_manager.get_by_id(user_id, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Progetto non trovato")
    try:
        msg_type = WarRoomMessageType(payload.message_type)
    except ValueError:
        raise HTTPException(status_code=422, detail="Tipo di messaggio non valido")
    message = post_inter_agent_message(
        project, payload.sender_id, payload.recipient_id, payload.content[:1200], msg_type
    )
    if message is None:
        raise HTTPException(status_code=400, detail="Dialogo non consentito")
    project_manager.save(user_id, project)
    return {"status": "success", "message": message.model_dump()}

@project_router.post("/projects/{project_id}/agents/escalate")
async def escalate_specialist(project_id: str, payload: AgentEscalatePayload, user_id: str = "user_primary"):
    project = project_manager.get_by_id(user_id, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Progetto non trovato")
    result = chief_supervisor.escalate_to_specialist(
        project, payload.requester_agent_id, payload.specialty[:80], payload.justification[:1200]
    )
    project_manager.save(user_id, project)
    return {"status": "success", "result": result}