import asyncio
import json
import logging
from typing import AsyncGenerator, Dict, Any, List, Optional

from .inference_service import StudioBrainUnavailable
from .models import Attachment, Message

log = logging.getLogger("nuxiva.ai_studio")


def _event(payload: Dict[str, Any]) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


class StreamingService:
    @staticmethod
    async def stream_message(
        service_ref,
        thread_id: str,
        content: str,
        attachments: Optional[List[Attachment]] = None,
        preset_id: Optional[str] = None,
        actor: str = "admin",
        model_mode: Optional[str] = None,
    ) -> AsyncGenerator[str, None]:
        yield _event({"type": "status", "state": "thinking"})
        try:
            msg: Message = await service_ref.send_message(
                thread_id=thread_id,
                content=content,
                attachments=attachments,
                preset_id=preset_id,
                actor=actor,
                model_mode=model_mode,
            )
        except StudioBrainUnavailable as exc:
            log.warning("AI Studio senza cervello disponibile: %s", exc)
            yield _event({"type": "error", "code": "brain_unavailable", "detail": str(exc)})
            return

        thought_chunks = msg.thought.split(" ") if msg.thought else []
        for i, word in enumerate(thought_chunks):
            token = word + (" " if i < len(thought_chunks) - 1 else "")
            yield _event({"type": "thought_delta", "token": token})
            await asyncio.sleep(0.004)

        content_chunks = msg.content.split(" ")
        for i, word in enumerate(content_chunks):
            token = word + (" " if i < len(content_chunks) - 1 else "")
            yield _event({"type": "token", "token": token})
            await asyncio.sleep(0.006)

        yield _event({"type": "done", "message": msg.to_dict()})
