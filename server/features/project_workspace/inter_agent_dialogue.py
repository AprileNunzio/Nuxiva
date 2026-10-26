from typing import Optional

from server.features.project_workspace.project_models import (
    ProjectStateExtended,
    WarRoomMessage,
    WarRoomMessageType,
)

_ALLOWED_TYPES = {
    WarRoomMessageType.THOUGHT,
    WarRoomMessageType.CRITIQUE,
    WarRoomMessageType.ACTION,
}


def post_inter_agent_message(
    project: ProjectStateExtended,
    sender_id: str,
    recipient_id: str,
    content: str,
    message_type: WarRoomMessageType = WarRoomMessageType.THOUGHT,
    sender_name: Optional[str] = None,
) -> Optional[WarRoomMessage]:
    if message_type not in _ALLOWED_TYPES:
        return None
    if sender_id not in project.assigned_agents or recipient_id not in project.assigned_agents:
        return None
    message = WarRoomMessage(
        sender_id=sender_id,
        sender_name=sender_name or sender_id,
        sender_role="agent",
        message_type=message_type,
        content=content,
        metadata={"recipient": recipient_id, "inter_agent": True},
    )
    project.war_room_feed.append(message)
    return message
