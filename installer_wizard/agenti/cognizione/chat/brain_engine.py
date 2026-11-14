import time

from agenti.mcpclient import brain

FAILED_REPLY = "Ho provato a eseguire l'azione ma non è andata a buon fine."


async def answer(text: str, slug: str) -> dict | None:
    outcome = await brain.attempt(text, slug or "guest", int(time.time() * 1000))
    if outcome is None:
        return None
    if outcome.pop("failed", False):
        outcome["reply"] = FAILED_REPLY
        outcome["exact_reply"] = True
    return outcome
