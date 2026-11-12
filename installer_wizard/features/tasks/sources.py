import time

from features.agency import board
from features.agency.client import AgencyRejected, AgencyUnavailable

STATE_OF = {
    "planning": "running",
    "running": "running",
    "waiting_user": "running",
    "paused": "paused",
    "completed": "done",
    "failed": "error",
    "cancelled": "cancelled",
}
RECENT = 7 * 86400
PREFIX = "agency:"


async def projects() -> list[dict]:
    try:
        cards = (await board.overview())["projects"]
    except (AgencyUnavailable, AgencyRejected):
        return []
    now = time.time()
    rows: list[dict] = []
    for card in cards:
        state = STATE_OF.get(card["status"], "running")
        stamp = card["created_at_ms"] / 1000
        if state in ("done", "error", "cancelled") and now - stamp > RECENT:
            continue
        counts = card["counts"]
        rows.append({
            "id": PREFIX + card["id"],
            "kind": "project",
            "title": card["title"],
            "feature": "agency",
            "ref": card["id"],
            "state": state,
            "stage": "",
            "detail": "",
            "progress": card["percent"] / 100,
            "summary": f"{counts['done']}/{counts['total']}",
            "error": "",
            "created": stamp,
            "updated": stamp,
            "finished": 0.0,
            "result": {},
            "offer": None,
            "answered": True,
            "steps": [],
        })
    return rows
