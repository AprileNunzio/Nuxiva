import hashlib
import time
from typing import Any

from features.autonomous_worker.domain.models import CollabMessage, Mission
from features.autonomous_worker.domain.sanitizer import sanitize_text
from features.team.board import board


class CollabBus:
    def post(
        self,
        mission: Mission,
        sender_id: str,
        sender_role: str,
        content: str,
        target_id: str = "all",
        kind: str = "message",
        artifact_ref: str = "",
    ) -> CollabMessage:
        mid_hash = hashlib.sha256(f"{time.time()}:{sender_id}:{content}".encode("utf-8")).hexdigest()[:8]
        msg_id = f"msg_{mid_hash}"

        msg = CollabMessage(
            id=msg_id,
            sender_id=sanitize_text(sender_id, 40),
            sender_role=sanitize_text(sender_role, 60),
            target_id=sanitize_text(target_id, 40),
            channel=f"mission:{mission.id}",
            content=sanitize_text(content, 1000),
            kind=sanitize_text(kind, 30),
            artifact_ref=sanitize_text(artifact_ref, 200),
            timestamp=time.time(),
        )

        mission.collab_messages.append(msg)
        if len(mission.collab_messages) > 300:
            mission.collab_messages = mission.collab_messages[-300:]

        board.post(
            sender_role or "specialist",
            target_id if target_id != "all" else "tutti",
            f"[{mission.title[:30]}] {msg.content[:160]}",
            kind,
        )
        return msg

    def system_announce(self, mission: Mission, text: str, kind: str = "directive") -> CollabMessage:
        return self.post(
            mission=mission,
            sender_id="ceo",
            sender_role="CEO Executive",
            content=text,
            target_id="all",
            kind=kind,
        )

    def recent(self, mission: Mission, limit: int = 50) -> list[dict[str, Any]]:
        return [m.to_dict() for m in mission.collab_messages[-limit:]]


collab_bus = CollabBus()
