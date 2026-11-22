"""Servizio di streaming SSE token-by-token per AI Studio."""

import asyncio
import json
from typing import AsyncGenerator, Dict, Any, List, Optional
from .models import Attachment, Message


class StreamingService:
    @staticmethod
    async def stream_message(
        service_ref,
        thread_id: str,
        content: str,
        attachments: Optional[List[Attachment]] = None,
        preset_id: Optional[str] = None,
        actor: str = "admin",
    ) -> AsyncGenerator[str, None]:
        """Emette eventi SSE in formato: data: {"type": ..., ...}\n\n"""
        msg: Message = await service_ref.send_message(
            thread_id=thread_id,
            content=content,
            attachments=attachments,
            preset_id=preset_id,
            actor=actor,
        )

        thought_chunks = msg.thought.split(" ") if msg.thought else []
        for i, word in enumerate(thought_chunks):
            token = word + (" " if i < len(thought_chunks) - 1 else "")
            yield f"data: {json.dumps({'type': 'thought_delta', 'token': token})}\n\n"
            await asyncio.sleep(0.01)

        content_chunks = msg.content.split(" ")
        for i, word in enumerate(content_chunks):
            token = word + (" " if i < len(content_chunks) - 1 else "")
            yield f"data: {json.dumps({'type': 'token', 'token': token})}\n\n"
            await asyncio.sleep(0.015)

        done_payload: Dict[str, Any] = {
            "type": "done",
            "message": msg.to_dict(),
        }
        yield f"data: {json.dumps(done_payload)}\n\n"
