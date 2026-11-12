import asyncio
import logging
import os
import time

import native_core
from agenti.brain.privacy.gate import privacy_gate
from agenti.brain.privacy.levels import PUBLIC

log = logging.getLogger("nuxiva.nodes.jev")


async def planner_kind(node: dict, text: str, body: dict) -> str:
    key = os.environ.get("TYPESAFE_API_KEY", "")
    enabled_nodes = os.environ.get("NUXIVA_JEV_WINDOWS_NODES", "").split(",")
    hardware = node.get("hardware") or {}
    context = body.get("context") or {}
    if (not key or not node.get("id") or node["id"] not in {item.strip() for item in enabled_nodes}
            or hardware.get("os", "").lower() != "windows" or len(text.encode("utf-8")) > 768
            or body.get("image") or body.get("results") or body.get("research_approved")
            or (isinstance(context, dict) and context.get("content"))):
        return "deep"
    if privacy_gate.level((text,)) != PUBLIC:
        return "deep"
    classify = native_core.symbol("jev_simple_windows_task")
    if classify is None:
        log.warning("Router Jev indisponibile nel runtime nativo")
        return "deep"
    started = time.monotonic()
    try:
        kind = "chat" if await asyncio.to_thread(classify, text, key) else "deep"
    except RuntimeError:
        log.warning("Classificazione Jev non disponibile, uso il planner standard")
        kind = "deep"
    log.info("Router Jev Windows: profilo=%s latenza_ms=%d", kind, int((time.monotonic() - started) * 1000))
    return kind
