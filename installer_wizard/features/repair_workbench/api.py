import re
import json
from pathlib import Path

import httpx
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse

from access import require_display
from core_client import core
from features.brain.bridge import _authorised

public_routes = APIRouter()
admin_routes = public_routes
_ID = r"[A-Za-z0-9_\-][A-Za-z0-9_.\-]{0,63}"
_READ = re.compile(rf"(?:sessions/{_ID}|launch-requests|projects)")
_WRITE = re.compile(rf"(?:sessions|projects|sessions/{_ID}/(?:analyze-frame|teach-component|chat|escalate))")
_MAX_BODY = 6_100_000


@admin_routes.post("/api/internal/repair-workbench/analyze")
async def internal_vision(request: Request):
    from features.brain import sight
    from features.brain.llm import BrainUnavailable
    from server.features.repair_workbench.frame_validator import decode_frame
    from server.features.repair_workbench.ollama_vision import PROMPT_TEMPLATE
    from server.features.repair_workbench.session_models import VisionObservation
    body = await _authorised(request, "/api/internal/repair-workbench/analyze", _MAX_BODY)
    try:
        data = json.loads(body)
        jpeg = decode_frame(data["frame_base64"])
        prompt = PROMPT_TEMPLATE.format(language=str(data.get("language", "it"))[:12],
                                        known=", ".join(data.get("known_refs", [])[:60]))
        result, model = await sight.look(jpeg, prompt, as_json=True, max_tokens=3000,
                                         validator=VisionObservation.model_validate)
        observation = VisionObservation.model_validate(result)
    except BrainUnavailable as exc:
        raise HTTPException(503, "vision_models_unavailable") from exc
    except (ValueError, KeyError, TypeError) as exc:
        raise HTTPException(422, "invalid_vision_request") from exc
    return {**observation.model_dump(mode="json"), "model_used": model}


@public_routes.get("/repair-workbench")
async def workbench_page(request: Request):
    require_display(request)
    index = Path(__file__).resolve().parents[3] / "client_web" / "dist" / "index.html"
    if not index.is_file():
        raise HTTPException(503, "workbench_client_unavailable")
    return FileResponse(index, headers={"Cache-Control": "no-store"})


@public_routes.api_route("/api/v1/repair-workbench/{path:path}", methods=["GET", "POST"])
async def workbench_proxy(path: str, request: Request):
    require_display(request)
    pattern = _READ if request.method == "GET" else _WRITE
    if not pattern.fullmatch(path):
        raise HTTPException(404, "workbench_endpoint_not_found")
    if request.method == "POST" and request.headers.get("X-Nuxiva-Request") != "1":
        raise HTTPException(403, "invalid_request")
    payload = None
    if request.method == "POST":
        data = bytearray()
        async for chunk in request.stream():
            data.extend(chunk)
            if len(data) > _MAX_BODY:
                raise HTTPException(413, "frame_too_large")
        try:
            payload = json.loads(data)
        except (ValueError, UnicodeDecodeError) as exc:
            raise HTTPException(400, "invalid_request") from exc
        if not isinstance(payload, dict):
            raise HTTPException(400, "invalid_request")
    target = "/api/v1/projects" if path == "projects" else f"/api/v1/repair-workbench/{path}"
    params = {"user_id": "user_primary"}
    if path == "launch-requests":
        params["since"] = request.query_params.get("since", "0")
    try:
        response = await core.request(request.method, target, params=params, json=payload, timeout=150)
        return JSONResponse(response.json(), status_code=response.status_code, headers={"Cache-Control": "no-store"})
    except (httpx.HTTPError, ValueError) as exc:
        raise HTTPException(502, "workbench_core_unavailable") from exc
