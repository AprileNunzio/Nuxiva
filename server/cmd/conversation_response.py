from typing import AsyncGenerator

from anyio import CancelScope
from fastapi.responses import StreamingResponse
from starlette.types import Send


class ConversationResponse(StreamingResponse):
    def __init__(self, events: AsyncGenerator[str, None]):
        super().__init__(events, media_type="text/event-stream",
                         headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"})
        self.events = events

    async def stream_response(self, send: Send) -> None:
        try:
            await super().stream_response(send)
        finally:
            with CancelScope(shield=True):
                await self.events.aclose()
