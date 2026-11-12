from typing import Any, Dict

from server.core.agent_registry.forge import agent_forge
from server.config.env import settings
from server.features.llm_gateway.contracts import LLMMessage, LLMRequest
from server.features.llm_gateway.gateway import llm_gateway
from server.features.project_workspace.chief_supervisor import chief_supervisor
from server.features.project_workspace.manager import project_manager
from server.features.project_workspace.project_models import (
    WarRoomMessage,
    WarRoomMessageType,
)
from server.features.repair_workbench.context_builder import build_session_context
from server.features.repair_workbench.session_models import AgentNote, Message
from server.features.repair_workbench.session_requests import (
    ChatRequest,
    EscalationRequest,
)
from server.features.repair_workbench.workbench_service import WorkbenchService
from server.shared.errors.domain_errors import (
    AgentExecutionException,
    EntityNotFoundException,
)

DEFAULT_AGENT_ID = "electronics_repair_engineer"


class WorkbenchCollaboration:
    def __init__(self, workbench: WorkbenchService) -> None:
        self._workbench = workbench

    def _project(self, owner_id: str, project_id: str):
        project = project_manager.get_by_id(owner_id, project_id)
        if project is None:
            raise EntityNotFoundException("project", project_id)
        return project

    async def chat(self, owner_id: str, session_id: str, request: ChatRequest) -> Dict[str, Any]:
        session = self._workbench.get(owner_id, session_id)
        project = self._project(owner_id, session.project_id)
        agent_id = request.agent_id or DEFAULT_AGENT_ID
        spec = agent_forge.get_agent(agent_id)
        if spec is None or agent_id not in project.assigned_agents:
            raise EntityNotFoundException("project_agent", agent_id)
        system_prompt = (
            f"{spec.system_prompt}\nReply in language '{session.language}'. "
            f"Current live board context:\n{build_session_context(session)}"
        )
        response = await llm_gateway.generate_completion(
            LLMRequest(
                model_name=settings.SYSTEM2_MODEL,
                component="repair_workbench_chat",
                system_prompt=system_prompt,
                messages=[
                    *[LLMMessage(role="assistant", content=note.message.text)
                      for note in session.notes[-8:] if note.message.text],
                    LLMMessage(role="user", content=request.message),
                ],
                temperature=0.3,
            )
        )
        if response.is_synthetic or not response.content:
            raise AgentExecutionException(agent_id, "LLM unavailable")
        project_manager.post_war_room_message(
            owner_id,
            session.project_id,
            WarRoomMessage(
                sender_id=owner_id,
                sender_name="Operator",
                sender_role="Human Overseer",
                message_type=WarRoomMessageType.USER_INPUT,
                content=request.message,
            ),
        )
        project_manager.post_war_room_message(
            owner_id,
            session.project_id,
            WarRoomMessage(
                sender_id=agent_id,
                sender_name=spec.name,
                sender_role=spec.role_category,
                message_type=WarRoomMessageType.ACTION,
                content=response.content,
            ),
        )
        reply = Message(text=response.content)
        session.notes.append(AgentNote(agent_id=agent_id, message=reply))
        session.notes = session.notes[-50:]
        self._workbench.remember(session)
        return {"agent_id": agent_id, "agent_name": spec.name, "reply": reply.model_dump()}

    def escalate(self, owner_id: str, session_id: str, request: EscalationRequest) -> Dict[str, Any]:
        session = self._workbench.get(owner_id, session_id)
        project = self._project(owner_id, session.project_id)
        result = chief_supervisor.escalate_to_specialist(
            project, request.requester_agent_id, request.specialty, request.justification
        )
        project_manager.save(owner_id, project)
        return result
