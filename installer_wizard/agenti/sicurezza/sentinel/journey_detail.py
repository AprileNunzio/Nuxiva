import re

from access import NO_CACHE, require_admin
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse

from agenti.authz.access_control import account, require_permission
from agenti.brain.journey import journeys
from agenti.sentinel import record
from agenti.system_logs.service import redact

routes = APIRouter()
JOURNEY_ID = re.compile(r"[0-9a-f]{12}")


@routes.get("/api/sentinel/journeys/{journey_id}", openapi_extra={"x-nuxiva-capabilities": ["sentinel.read"]})
def detail(journey_id: str, user: str = Depends(require_admin)):
    require_permission(user, "sentinel.read")
    if account(user)["role"] != "owner":
        raise HTTPException(403, "sentinel_journey_owner_required")
    if not record.enabled() or not JOURNEY_ID.fullmatch(journey_id):
        raise HTTPException(404, "sentinel_journey_unavailable")
    journey = next((item for item in journeys.snapshot()["journeys"] if item["id"] == journey_id), None)
    if journey is None:
        raise HTTPException(404, "sentinel_journey_unavailable")
    record.record("sentinel.read", record.NUXIVA, "sentinel.sentinel.read", {"user": user}, source="sentinel")
    return JSONResponse({
        "id": journey_id,
        "question": redact(journey["query"]),
        "answer": redact(journey["answer"]),
        "state": journey["state"],
        "elapsed": journey["elapsed"],
        "steps": [{"id": step["i"], "kind": step["k"], "state": step["s"],
                   "name": redact(step["n"]), "detail": redact(step["d"]),
                   "start": step["a"], "end": step["b"]} for step in journey["nodes"]],
    }, headers=NO_CACHE)
