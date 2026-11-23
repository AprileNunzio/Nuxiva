import asyncio
import base64
import binascii
import json
import threading
import time

import httpx
import numpy as np
from config import NODE
from core_client import core
from fastapi import APIRouter, HTTPException, Request

from agenti.nodes import deviceauth
from agenti.nodes.registry import registry

public_routes = APIRouter()

MAX_FRAME = 1536 * 1024
MAX_FRAME_BODY = MAX_FRAME * 4 // 3 + 4096
MIN_FRAME_GAP = 0.25
VOICE_RATE = 16000
MAX_VOICE_SECONDS = 30
MAX_VOICE = VOICE_RATE * 2 * MAX_VOICE_SECONDS
MAX_VOICE_BODY = MAX_VOICE * 4 // 3 + 4096
JPEG = b"\xff\xd8\xff"
LANG_LIMIT = 8


class FrameGate:
    def __init__(self, gap: float) -> None:
        self.gap = gap
        self.last: dict[str, float] = {}
        self.lock = threading.Lock()

    def accept(self, node_id: str, now: float) -> bool:
        with self.lock:
            if len(self.last) > 512:
                self.last = {k: v for k, v in self.last.items() if now - v < self.gap}
            if now - self.last.get(node_id, 0.0) < self.gap:
                return False
            self.last[node_id] = now
            return True


frames = FrameGate(MIN_FRAME_GAP)


async def _signed_node(request: Request, scope: str, limit: int) -> tuple[dict, dict]:
    if int(request.headers.get("content-length") or 0) > limit:
        raise HTTPException(413, "payload_too_large")
    auth = request.headers.get("authorization", "")
    try:
        node = registry.authenticate(request.headers.get("x-nuxiva-node", ""), auth.removeprefix("Bearer ").strip())
    except PermissionError as exc:
        raise HTTPException(401, str(exc))
    if not getattr(request.state, "device_verified", False):
        raise HTTPException(401, "node.error.signature")
    deviceauth.require_scope(node, scope)
    body = await request.body()
    if len(body) > limit:
        raise HTTPException(413, "payload_too_large")
    try:
        data = json.loads(body)
    except ValueError:
        raise HTTPException(400, "invalid_request")
    if not isinstance(data, dict):
        raise HTTPException(400, "invalid_request")
    return node, data


def _decode(raw, ceiling: int) -> bytes:
    if not isinstance(raw, str) or not raw or len(raw) > ceiling * 4 // 3 + 4:
        raise HTTPException(400, "invalid_media")
    try:
        data = base64.b64decode(raw, validate=True)
    except (binascii.Error, ValueError):
        raise HTTPException(400, "invalid_media")
    if not data or len(data) > ceiling:
        raise HTTPException(400, "invalid_media")
    return data


def pcm_to_float(pcm: bytes) -> np.ndarray:
    if len(pcm) % 2:
        raise HTTPException(400, "invalid_media")
    return np.frombuffer(pcm, dtype="<i2").astype(np.float32) / 32768.0


@public_routes.post("/api/nodes/vision/feed")
async def node_vision_feed(request: Request):
    node, body = await _signed_node(request, "camera.stream", MAX_FRAME_BODY)
    frame = _decode(body.get("frame"), MAX_FRAME)
    if not frame.startswith(JPEG):
        raise HTTPException(415, "invalid_media")
    if not frames.accept(node["id"], time.monotonic()):
        raise HTTPException(429, "rate_limited")
    payload = {"device_id": node["id"], "frame_base64": base64.b64encode(frame).decode("ascii"), "timestamp": time.time()}
    try:
        reply = await core.request("POST", "/api/v1/vision/feed", json=payload, timeout=15)
    except httpx.HTTPError:
        raise HTTPException(502, "core_unavailable")
    if reply.status_code != 200:
        raise HTTPException(502, "core_rejected")
    return {"accepted": True}


@public_routes.post("/api/nodes/voice")
async def node_voice(request: Request):
    node, body = await _signed_node(request, "audio.capture", MAX_VOICE_BODY)
    if body.get("rate") != VOICE_RATE:
        raise HTTPException(400, "invalid_rate")
    audio = pcm_to_float(_decode(body.get("pcm16"), MAX_VOICE))
    from agenti.ear import stt
    text, lang = await asyncio.to_thread(stt.transcribe, audio, False, True)
    if not text.strip():
        return {"transcript": "", "reply": None}
    from agenti.chat.api import assistant_chat
    NODE.set(node["id"])
    requested = str(body.get("lang") or "")[:LANG_LIMIT] or lang
    return await assistant_chat(text, node["id"], requested or None)
