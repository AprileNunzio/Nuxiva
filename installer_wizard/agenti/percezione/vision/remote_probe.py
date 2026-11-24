import asyncio
import threading
import time

import cv2
import numpy as np
from fastapi import APIRouter, HTTPException, Request

import selection
from remote_frame import HEIGHT, WIDTH, read_frame
from remote_verdict import LivenessBook, face_outcome, identity_outcome
from views import face_engine

SESSION_HEADER = "x-nuxiva-probe-session"


def router(views, gallery) -> APIRouter:
    routes = APIRouter()
    worker = threading.Lock()
    liveness = LivenessBook(face_engine.liveness)

    def probe(data: bytes, session: str) -> dict:
        if not worker.acquire(blocking=False):
            raise HTTPException(429, "camera.frame.busy")
        try:
            rgba = np.frombuffer(data, dtype=np.uint8).reshape((HEIGHT, WIDTH, 4))
            frame = cv2.cvtColor(rgba, cv2.COLOR_RGBA2BGR)
            with views.lock:
                views.detector.setInputSize((WIDTH, HEIGHT))
                _, faces = views.detector.detect(frame)
                rejected = face_outcome(faces)
                if rejected:
                    return {"outcome": rejected, "liveness": "unknown"}
                aligned = views.recognizer.alignCrop(frame, faces[0])
                feature = views.recognizer.feature(aligned).flatten()
            alive = liveness.update(session, [float(v) for v in faces[0][4:14]], time.time(),
                                    selection.liveness_minimum())
            verdict = gallery.match_ex(feature, marks=face_engine.marks_of(aligned))
            return identity_outcome(verdict, len(gallery.people), alive)
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
        return await asyncio.to_thread(probe, data, request.headers.get(SESSION_HEADER, ""))

    return routes
