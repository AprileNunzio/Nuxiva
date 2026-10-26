from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from server.core.agent_registry.forge import agent_forge
from server.core.agent_registry.catalog import AgentCapabilitySpec
from server.core.agent_registry.agent_workspace_service import (
    agent_workspace_service,
    AgentWorkspaceProfile,
)

agent_registry_router = APIRouter()

class KnowledgeUploadPayload(BaseModel):
    filename: str
    content: str

class InstructionsUpdatePayload(BaseModel):
    instructions: str

class ToolScriptUploadPayload(BaseModel):
    tool_name: str
    python_code: str

@agent_registry_router.get("/agents/catalog")
async def list_agent_catalog():
    agents = agent_forge.list_all_agents()
    return {"status": "success", "catalog": [a.model_dump() for a in agents]}

@agent_registry_router.post("/agents/forge")
async def forge_custom_agent(payload: AgentCapabilitySpec):
    created = agent_forge.forge_custom_agent(payload)
    return {"status": "success", "agent": created.model_dump()}

@agent_registry_router.delete("/agents/forge/{agent_id}")
async def delete_custom_agent(agent_id: str):
    ok = agent_forge.delete_custom_agent(agent_id)
    if not ok:
        raise HTTPException(status_code=400, detail="Impossibile eliminare l'agente")
    return {"status": "success"}

@agent_registry_router.get("/agents/{agent_id}/workspace")
async def get_agent_workspace_details(agent_id: str):
    ws = agent_workspace_service.get_workspace(agent_id)
    if not ws:
        raise HTTPException(status_code=404, detail="Workspace agente non trovato")
    return {"status": "success", "workspace": ws.model_dump()}

@agent_registry_router.post("/agents/{agent_id}/workspace/profile")
async def update_agent_workspace_profile(agent_id: str, payload: AgentWorkspaceProfile):
    updated = agent_workspace_service.update_profile(agent_id, payload)
    return {"status": "success", "profile": updated.model_dump()}

@agent_registry_router.post("/agents/{agent_id}/workspace/instructions")
async def update_agent_workspace_instructions(agent_id: str, payload: InstructionsUpdatePayload):
    updated = agent_workspace_service.update_instructions(agent_id, payload.instructions)
    return {"status": "success", "instructions": updated}

@agent_registry_router.post("/agents/{agent_id}/workspace/knowledge")
async def upload_agent_knowledge(agent_id: str, payload: KnowledgeUploadPayload):
    doc = agent_workspace_service.add_or_update_knowledge(agent_id, payload.filename, payload.content)
    return {"status": "success", "document": doc.model_dump()}

@agent_registry_router.delete("/agents/{agent_id}/workspace/knowledge/{filename}")
async def delete_agent_knowledge(agent_id: str, filename: str):
    ok = agent_workspace_service.delete_knowledge(agent_id, filename)
    if not ok:
        raise HTTPException(status_code=404, detail="File non trovato")
    return {"status": "success"}

@agent_registry_router.post("/agents/{agent_id}/workspace/tools")
async def upload_agent_custom_tool(agent_id: str, payload: ToolScriptUploadPayload):
    saved_name = agent_workspace_service.add_custom_tool_script(agent_id, payload.tool_name, payload.python_code)
    return {"status": "success", "tool_name": saved_name}
