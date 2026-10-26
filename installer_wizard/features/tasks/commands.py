import re

from features.tasks.api import snapshot

FACE = {"mode": "face"}
ASK = re.compile(r"\b(?:attivit[aà]|task|lavori|cosa\s+stai\s+facendo|a\s+che\s+punto\s+sei|sei\s+ancora\s+al\s+lavoro|hai\s+finito|in\s+background)\b.*|\b(?:hai\s+finito|a\s+che\s+punto)\b", re.I)
STRICT = re.compile(r"\b(?:attivit[aà]\s+in\s+corso|cosa\s+stai\s+facendo|a\s+che\s+punto\s+sei|hai\s+finito|sei\s+ancora\s+al\s+lavoro|lavori\s+in\s+background|task\s+attiv\w+)\b", re.I)


async def answer(text: str) -> tuple[str, dict]:
    if not STRICT.search(text):
        raise LookupError("tasks")
    data = snapshot()
    active = [t for t in data["tasks"] if t["state"] in ("queued", "running")]
    waiting = [t for t in data["tasks"] if t["state"] == "done" and t.get("offer") and not t.get("answered")]
    parts = []
    if active:
        parts.append("In corso: " + "; ".join(f"«{t['title']}» al {round(t['progress'] * 100)}%" + (f" ({t['stage']})" if t["stage"] else "") for t in active[:5]) + ".")
    if waiting:
        parts.append("Pronto: " + "; ".join(f"«{t['title']}»" for t in waiting[:5]) + ". Vuoi ascoltarlo, aprirlo o parlarne?")
    return (" ".join(parts) or "Non ho attività in corso: tutto il lavoro è concluso."), FACE
