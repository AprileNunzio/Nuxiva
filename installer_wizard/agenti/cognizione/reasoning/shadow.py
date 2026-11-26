import asyncio
import contextvars
import json

import tasks
from state import store

from agenti.reasoning import models, pipeline, state, traces
from agenti.reasoning.contracts import CHAT, CONNECTOR

CONVERSATION = ("conversation", "chat")
_busy = asyncio.Lock()


def track() -> contextvars.Token:
    from agenti.agent import registry
    return registry.USED.set([])


def untrack(token: contextvars.Token) -> list[str]:
    from agenti.agent import registry
    used = registry.USED.get() or []
    registry.USED.reset(token)
    return list(dict.fromkeys(used))


def legacy_capabilities(result: dict, used: list[str], connectors) -> list[str] | None:
    intent = str(result.get("intent") or "")
    if used:
        return used
    if intent in connectors:
        return [f"{CONNECTOR}{intent}"]
    if intent in CONVERSATION:
        return [CHAT]
    return None


async def observe(text: str, role: str, result: dict, used: list[str], connectors) -> None:
    if _busy.locked():
        return
    async with _busy:
        try:
            thought = await pipeline.think(text, role)
        except (models.ModelFailed, state.Unavailable) as exc:
            store.event("WARN", f"Motore in ombra non disponibile: {exc}", "reasoning")
            return
        engine = state.engine()
        legacy = legacy_capabilities(result, used, connectors)
        agreed = False
        if thought.valid and legacy is not None:
            agreement = json.loads(engine.compare(json.dumps(thought.checked["plan"]), json.dumps(legacy)))
            agreed = agreement["matches"]
        sample = {"comparable": legacy is not None, "agreed": agreed, "valid": thought.valid,
                  "missing": bool((thought.checked or {}).get("missing")), "cached": bool((thought.checked or {}).get("cached")),
                  "latency_ms": min(thought.latency_ms, 2**31), "tokens": min(thought.tokens, 2**31)}
        engine.record(json.dumps(sample), state.now_ms())
        traces.add("shadow", thought.public(), legacy=legacy, agreed=agreed, legacy_intent=str(result.get("intent") or ""))
        try:
            state.save()
        except OSError as exc:
            store.event("WARN", f"Registro del motore non salvato: {exc}", "reasoning")


def schedule(text: str, role: str, result: dict, used: list[str], connectors) -> None:
    if not state.ready() or state.emergency_off():
        return
    try:
        observing = json.loads(state.engine().status(state.now_ms()))["switch"]["mode"] == "shadow"
    except state.Unavailable:
        return
    if observing and result.get("reply"):
        tasks.background(observe(text, role, result, used, connectors))
