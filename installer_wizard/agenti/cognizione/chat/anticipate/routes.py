from access import require_display
from fastapi import APIRouter, HTTPException, Request
from tasks import background

from agenti.chat.anticipate import service, warmup
from agenti.chat.anticipate.budget import Budget
from agenti.desktop.display_scope import is_host_display

router = APIRouter()
thoughts = Budget(8)
warmups = Budget(4)


@router.post("/api/assistant/anticipate")
async def anticipate(request: Request):
    require_display(request)
    try:
        body = await request.json()
    except ValueError as exc:
        raise HTTPException(400, "anticipate.body") from exc
    if not isinstance(body, dict):
        raise HTTPException(400, "anticipate.body")
    who = str(request.client.host if request.client else "local")
    device = "kiosk" if is_host_display(request) else "remote_display"
    text = body.get("text")
    queued = {"warm": False, "think": False}
    if warmups.take(who):
        background(warmup.warm())
        queued["warm"] = True
    if isinstance(text, str) and text.strip() and thoughts.take(who):
        background(service.think_ahead(text[:service.MAX_TEXT], device))
        queued["think"] = True
    return {"queued": queued, "stats": dict(service.stats)}
