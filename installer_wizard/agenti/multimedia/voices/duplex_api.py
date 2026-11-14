import asyncio
import logging
from urllib.parse import urlsplit

import auth
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from agenti.voices import duplex_voice, synthesis

log = logging.getLogger("nuxiva.voice.duplex.api")
public_routes = APIRouter()
admin_routes = APIRouter()
LOCAL = ("127.0.0.1", "::1", "localhost")
POLICY_VIOLATION = 1008
UNAVAILABLE = 1013
MAX_SEND_QUEUE = 8


def trusted(websocket: WebSocket) -> bool:
    if websocket.client and websocket.client.host in LOCAL:
        return True
    origin, host = websocket.headers.get("origin", ""), websocket.headers.get("host", "")
    if not origin or not host or urlsplit(origin).netloc.lower() != host.lower():
        return False
    return any(auth.verify(websocket.cookies.get(name)) for name in (auth.DISPLAY_COOKIE, auth.SESSION_COOKIE))


async def synthesize(text: str) -> bytes:
    return await synthesis.synthesize(text)


@public_routes.websocket("/api/voice/duplex/ws")
async def duplex_socket(websocket: WebSocket):
    local = bool(websocket.client and websocket.client.host in LOCAL)
    device = "kiosk" if local else "remote_display"
    if not trusted(websocket):
        await websocket.close(code=POLICY_VIOLATION)
        return
    if not duplex_voice.enabled():
        await websocket.close(code=UNAVAILABLE)
        return
    await websocket.accept()
    lock = asyncio.Lock()

    async def send_json(doc: dict) -> None:
        async with lock:
            await websocket.send_json(doc)

    async def send_bytes(data: bytes) -> None:
        async with lock:
            await websocket.send_bytes(data)

    session = duplex_voice.VoiceSession(device, send_json, send_bytes, synthesize)
    if not duplex_voice.attach(device, session):
        await websocket.close(code=UNAVAILABLE)
        return
    try:
        while True:
            await session.handle(await websocket.receive_text())
    except WebSocketDisconnect:
        log.debug("Schermo scollegato dalla voce duplex")
    finally:
        duplex_voice.detach(device, session)
        await session.stop()
