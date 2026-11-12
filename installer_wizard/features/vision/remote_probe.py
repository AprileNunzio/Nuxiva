import asyncio
import threading

import cv2
import numpy as np
from fastapi import APIRouter, HTTPException, Request

from remote_frame import HEIGHT, WIDTH, read_frame
from views import face_engine


def router(views, gallery) -> APIRouter:
    routes = APIRouter()
    worker = threading.Lock()

    def probe(data: bytes) -> dict:
        if not worker.acquire(blocking=False):
            raise HTTPException(429, "camera.frame.busy")
        try:
            rgba = np.frombuffer(data, dtype=np.uint8).reshape((HEIGHT, WIDTH, 4))
            frame = cv2.cvtColor(rgba, cv2.COLOR_RGBA2BGR)
            with views.lock:
                views.detector.setInputSize((WIDTH, HEIGHT))
                _, faces = views.detector.detect(frame)
                if faces is None or len(faces) != 1 or faces[0][2] < 48:
                    return {"matched": False}
                aligned = views.recognizer.alignCrop(frame, faces[0])
                feature = views.recognizer.feature(aligned).flatten()
            verdict = gallery.match_ex(feature, marks=face_engine.marks_of(aligned))
            return {"matched": bool(verdict["slug"] and not verdict["ambiguous"])}
        finally:
            worker.release()

    @routes.post("/internal/remote-camera/probe")
    async def remote_camera_probe(request: Request):
        if not request.client or request.client.host not in ("127.0.0.1", "::1") or request.headers.get("origin"):
            raise HTTPException(403, "camera.frame.internal")
        if not isinstance(gallery.engine, face_engine.NativeFaceBook):
            raise HTTPException(503, "camera.frame.native_unavailable")
        try:
            async with asyncio.timeout(3):
                data = await read_frame(request)
        except TimeoutError as exc:
            raise HTTPException(408, "camera.frame.timeout") from exc
        return await asyncio.to_thread(probe, data)

    return routes
