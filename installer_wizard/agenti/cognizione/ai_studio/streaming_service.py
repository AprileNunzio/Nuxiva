import asyncio
import json
import logging
from typing import Any, AsyncGenerator, Dict, List, Optional

from .inference_service import StudioBrainUnavailable
from .models import Attachment, Message
from .token_stream import StreamRelay, listening

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
        queue: "asyncio.Queue[Dict[str, Any]]" = asyncio.Queue()
        relay = StreamRelay(queue)

        async def run() -> Message:
            with listening(relay):
                return await service_ref.send_message(
                    thread_id=thread_id,
                    content=content,
                    attachments=attachments,
                    preset_id=preset_id,
                    actor=actor,
                    model_mode=model_mode,
                )

        yield _event({"type": "status", "state": "thinking"})
        task = asyncio.create_task(run())
        getter: Optional[asyncio.Future] = None
        try:
            while True:
                getter = asyncio.ensure_future(queue.get())
                done, _ = await asyncio.wait({task, getter}, return_when=asyncio.FIRST_COMPLETED)
                if getter in done:
                    yield _event(getter.result())
                    continue
                getter.cancel()
                break
            relay.close()
            while not queue.empty():
                yield _event(queue.get_nowait())
            try:
                msg = task.result()
            except StudioBrainUnavailable as exc:
                log.warning("AI Studio senza cervello disponibile: %s", exc)
                yield _event({"type": "error", "code": "brain_unavailable", "detail": str(exc)})
                return
            yield _event({"type": "done", "message": msg.to_dict()})
        finally:
            if getter is not None and not getter.done():
                getter.cancel()
            if not task.done():
                task.cancel()
