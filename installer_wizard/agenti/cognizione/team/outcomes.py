import json
from functools import lru_cache
from pathlib import Path

_STATUS = {
    "success": "completed", "succeeded": "completed", "completed": "completed", "ok": "completed", "done": "completed",
    "failed": "failed", "failure": "failed", "error": "failed", "blocked": "blocked", "refused": "blocked",
    "denied": "blocked", "cancelled": "cancelled", "canceled": "cancelled", "pending": "pending",
    "awaiting_approval": "pending", "awaiting_confirmation": "pending", "running": "running", "started": "running",
    "started_in_background": "running", "in_progress": "running", "unverified": "unverified",
}
_PRIORITY = {"failed": 6, "blocked": 5, "cancelled": 4, "pending": 3, "running": 2, "completed": 1, "unverified": 0}


def execution_outcome(result: dict) -> dict:
    sources = [result]
    for key in ("result_data", "outcome"):
        if isinstance(result.get(key), dict):
            sources.append(result[key])
    nested = result.get("result_data")
    if isinstance(nested, dict) and isinstance(nested.get("outcome"), dict):
        sources.append(nested["outcome"])
    statuses, verified, verification_failed, cached = [], False, False, False
    for source in sources:
        status = source.get("status") or source.get("execution_status")
        if isinstance(status, str) and status.lower() in _STATUS:
            statuses.append((_STATUS[status.lower()], status))
        if isinstance(source.get("ok"), bool):
            statuses.append(("completed" if source["ok"] else "failed", "ok"))
        if isinstance(source.get("success"), bool):
            statuses.append(("completed" if source["success"] else "failed", "success"))
        if source.get("error") or source.get("errors"):
            statuses.append(("failed", "error"))
        verification = source.get("verification")
        verification_status = verification.get("status") if isinstance(verification, dict) else verification
        verified = verified or source.get("verified") is True or verification_status == "verified"
        verification_failed = verification_failed or source.get("verified") is False or verification_status in ("failed", "unverified")
        cached = cached or source.get("cache_hit") is True
    status, source_status = max(statuses, key=lambda row: _PRIORITY[row[0]], default=("unverified", ""))
    if status == "unverified" and verified and not verification_failed and not cached:
        status = "completed"
    confirmed = status == "completed" and verified and not verification_failed and not cached
    return {"status": status, "verified": confirmed, "verification": "verified" if confirmed else "unverified",
            "source_status": source_status}


@lru_cache(maxsize=4)
def messages(language: str) -> dict:
    language = language if language in {"it", "en", "fr", "es"} else "it"
    path = Path(__file__).with_name("language") / f"{language}.json"
    return json.loads(path.read_text(encoding="utf-8"))["outcomes"]


def describe(outcome: dict, agent: str, language: str = "it") -> tuple[str, str]:
    status = outcome["status"]
    key = "verified" if outcome["verified"] else "completed_unverified" if status == "completed" else status
    kind = "conferma" if outcome["verified"] else "errore" if status in {"failed", "blocked"} else "verifica"
    return messages(language)[key].format(agent=agent), kind
