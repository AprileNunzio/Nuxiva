import json
import logging
import re
import time
from urllib.parse import urlsplit

import auth
from access import NO_CACHE, require_admin
from fastapi import APIRouter, Depends, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse

from features.hands import events as hand_events
from features.hands import native, store

log = logging.getLogger("nuxiva.hands")
admin_routes = APIRouter()
public_routes = APIRouter()
BODY_LIMIT = 65_536
FRAME_LIMIT = 32_768
MAX_FPS = 60
POLICY_VIOLATION = 1008
UNAVAILABLE = 1013
LOCAL = ("127.0.0.1", "::1", "localhost")
CONTEXT_RE = re.compile(r"^[a-z0-9_.-]{1,64}$")
ACTIONS = ("ui.click", "ui.back", "view.zoom_in", "view.zoom_out", "view.rotate", "nav.back", "nav.forward",
           "nav.home", "media.toggle", "media.next", "media.previous", "volume.up", "volume.down", "volume.mute",
           "assistant.listen", "assistant.stop", "feedback.positive", "feedback.negative", "screen.fullscreen",
           "screen.next", "screen.previous", "scene.run", "bus.publish")
CONTEXTS = ("*", "desktop", "widget", "studio_3d", "tv", "music", "games", "assistant")


def _view() -> dict:
    return {"native": native.available(), "profile": store.load(), "catalog": native.catalog(),
            "actions": ACTIONS, "contexts": CONTEXTS, "recent": hand_events.recent()}


def _ready() -> None:
    if not native.available():
        raise HTTPException(503, "hands_native_unavailable")


@admin_routes.get("/api/hands/profile")
async def hands_profile(_: str = Depends(require_admin)):
    return JSONResponse(_view(), headers=NO_CACHE)


@admin_routes.put("/api/hands/profile")
async def hands_save(request: Request, _: str = Depends(require_admin)):
    _ready()
    raw = await request.body()
    if len(raw) > BODY_LIMIT:
        raise HTTPException(413, "hands_body_too_large")
    try:
        store.save(json.loads(raw or b"null"))
    except (ValueError, UnicodeDecodeError) as exc:
        raise HTTPException(400, str(exc)[:200]) from exc
    return JSONResponse(_view(), headers=NO_CACHE)


@admin_routes.post("/api/hands/profile/reset")
async def hands_reset(_: str = Depends(require_admin)):
    _ready()
    store.reset()
    return JSONResponse(_view(), headers=NO_CACHE)


@admin_routes.get("/api/hands/recent")
async def hands_recent(_: str = Depends(require_admin)):
    return JSONResponse({"recent": hand_events.recent()}, headers=NO_CACHE)


def _trusted(websocket: WebSocket) -> bool:
    if websocket.client and websocket.client.host in LOCAL:
        return True
    origin = websocket.headers.get("origin", "")
    host = websocket.headers.get("host", "")
    if not origin or not host or urlsplit(origin).netloc.lower() != host.lower():
        return False
    return any(auth.verify(websocket.cookies.get(name)) for name in (auth.DISPLAY_COOKIE, auth.SESSION_COOKIE))


def _context_switch(message: str) -> str:
    if len(message) > 128 or not message.startswith('{"context"'):
        return ""
    try:
        value = json.loads(message).get("context", "")
    except ValueError:
        return ""
    return value if isinstance(value, str) and CONTEXT_RE.match(value) else ""


class _Session:
    def __init__(self) -> None:
        self.revision = -1
        self.engine = None
        self.window = time.monotonic()
        self.frames = 0

    def current(self):
        if self.revision != store.revision() or self.engine is None:
            self.revision = store.revision()
            self.engine = native.engine(store.load())
        return self.engine

    def allow(self) -> bool:
        now = time.monotonic()
        if now - self.window >= 1.0:
            self.window, self.frames = now, 0
        self.frames += 1
        return self.frames <= MAX_FPS


@public_routes.websocket("/api/hands/ws")
async def hands_socket(websocket: WebSocket):
    if not _trusted(websocket):
        await websocket.close(code=POLICY_VIOLATION)
        return
    if not native.available():
        await websocket.close(code=UNAVAILABLE)
        return
    context = websocket.query_params.get("context", "desktop")
    context = context if CONTEXT_RE.match(context) else "desktop"
    await websocket.accept()
    session = _Session()
    try:
        while True:
            message = await websocket.receive_text()
            if len(message) > FRAME_LIMIT or not session.allow():
                continue
            switched = _context_switch(message)
            if switched:
                context = switched
                continue
            try:
                events = json.loads(session.current().feed_json(message, context))
            except ValueError:
                continue
            if events:
                hand_events.record(events)
                await websocket.send_text(json.dumps(events, separators=(",", ":")))
    except WebSocketDisconnect:
        log.debug("Display disconnesso dai gesti")
