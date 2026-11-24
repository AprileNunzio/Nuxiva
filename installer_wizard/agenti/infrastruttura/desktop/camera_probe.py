import asyncio

import httpx
from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse

from access import NO_CACHE, require_admin
from config import env_get
from agenti.desktop.camera_sessions import SESSION_HEADER, camera_owner, camera_sessions, require_camera_enabled
from agenti.desktop.remote_presence import judge, probe_session, remote_presence, viewer
from agenti.vision.proxy import VISION_URL
from agenti.vision.remote_frame import CONTENT_TYPE, read_frame

_probe_slot = asyncio.Lock()


def require_probe_enabled() -> None:
    require_camera_enabled()
    if env_get("NUXIVA_REMOTE_CAMERA_PROBE", "0") != "1":
        raise HTTPException(403, "camera.frame.disabled")


async def probe_camera(request: Request):
    require_admin(request)
    owner = camera_owner(request)
    require_probe_enabled()
    token = request.headers.get(SESSION_HEADER, "")
    camera_sessions.admit_frame(token, owner)
    if _probe_slot.locked():
        raise HTTPException(429, "camera.frame.busy")
    async with _probe_slot:
        try:
            async with asyncio.timeout(3):
                frame = await read_frame(request)
            async with httpx.AsyncClient(timeout=4, trust_env=False) as client:
                result = await client.post(f"{VISION_URL}/internal/remote-camera/probe", content=frame,
                                           headers={"Content-Type": CONTENT_TYPE,
                                                    "X-Nuxiva-Probe-Session": probe_session(token)})
            if result.status_code == 429:
                raise HTTPException(429, "camera.frame.busy")
            result.raise_for_status()
            payload = result.json()
        except TimeoutError as exc:
            raise HTTPException(408, "camera.frame.timeout") from exc
        except (httpx.HTTPError, ValueError) as exc:
            raise HTTPException(503, "camera.frame.unavailable") from exc
    require_probe_enabled()
    if camera_owner(request) != owner or not camera_sessions.active(token, owner):
        raise HTTPException(404, "camera.session.expired")
    verdict = judge(payload, _role(payload), _liveness_mode())
    return JSONResponse(remote_presence.settle(viewer(request), verdict), headers=NO_CACHE)


def _role(payload) -> str:
    slug = str(payload.get("slug") or "") if isinstance(payload, dict) else ""
    if not slug:
        return ""
    from agenti.people import people
    return str((people.load(slug) or {}).get("role") or "guest")


def _liveness_mode() -> str:
    from agenti.vision import selection
    return selection.liveness_mode()
