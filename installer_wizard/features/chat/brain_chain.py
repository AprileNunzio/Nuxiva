import asyncio
import time
from itertools import groupby
from typing import Any

import httpx
from state import store
from tasks import background

from features.brain.brains import brains
from features.brain.residency import touch
from features.brain.trace import trace
from features.cloud import conversation
from features.cloud.catalog import is_cloud
from features.cloud.client import CloudError


class NoBrainAvailable(RuntimeError):
    pass


def _label(kind: str) -> str:
    return "Nuxiva 5.0 Veloce (5.0-flash)" if kind == "chat" else "Nuxiva 5.0 Pro Ragionamento (5.0-pro)"


async def _cloud(ref: str, query: str, device: str, context: dict, route: dict) -> dict:
    started = time.time()
    call = trace.begin("conversation", route["reason"], route["models"])
    trace.attempt(call, ref)
    try:
        answer = await conversation.reply(ref, query, device, context, route["max_tokens"])
    except CloudError as exc:
        brains.record(ref, (time.time() - started) * 1000, False, route["kind"])
        trace.abort(call, str(exc))
        raise
    brains.record(ref, answer.ms, True, route["kind"])
    trace.finish(call, ref, answer.ms, answer.text)
    background(touch(ref))
    return {
        "agent_id": f"nuxiva_cloud · {ref.removeprefix('cloud:')} ({_label(route['kind'])})",
        "speech_output": answer.text,
        "result_data": {"model": ref, "commercial_tier": _label(route["kind"])},
    }


async def _run_candidate(candidate_type: str, item: Any, query: str, device: str, context: dict, route: dict, core_local) -> dict:
    if candidate_type == "local":
        return await core_local(item)
    return await _cloud(item, query, device, context, route)


async def ask(query: str, device: str, context: dict, route: dict, core_local) -> dict:
    candidates = []
    for cloud, group in groupby(route["models"], key=is_cloud):
        names = list(group)
        if not cloud:
            candidates.append(("local", names))
        else:
            for ref in names:
                candidates.append(("cloud", ref))

    if not candidates:
        raise NoBrainAvailable("nessun cervello configurato")

    if route["kind"] == "chat" or len(candidates) == 1:
        errors = []
        for ctype, target in candidates:
            try:
                return await _run_candidate(ctype, target, query, device, context, route, core_local)
            except (httpx.HTTPError, ValueError) as exc:
                errors.append(f"locale: {type(exc).__name__}")
                store.event("WARN", f"Modello locale non disponibile: {exc}", "core")
            except CloudError as exc:
                errors.append(str(exc)[:160])
                store.event("WARN", f"Cervello cloud non disponibile: {exc}", "cloud")
        raise NoBrainAvailable("; ".join(errors) or "nessun cervello disponibile")

    tasks = []
    for ctype, target in candidates[:4]:
        task = asyncio.create_task(_run_candidate(ctype, target, query, device, context, route, core_local))
        tasks.append(task)

    errors = []
    while tasks:
        done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
        for completed_task in done:
            tasks.remove(completed_task)
            try:
                result = completed_task.result()
                for remaining in tasks:
                    if not remaining.done():
                        remaining.cancel()
                return result
            except (httpx.HTTPError, ValueError) as exc:
                errors.append(f"locale: {type(exc).__name__}")
                store.event("WARN", f"Modello speculativo locale fallito: {exc}", "core")
            except CloudError as exc:
                errors.append(str(exc)[:160])
                store.event("WARN", f"Cervello speculativo cloud fallito: {exc}", "cloud")
            except asyncio.CancelledError:
                pass

    raise NoBrainAvailable("; ".join(errors) or "tutte le corsie speculative corticali hanno fallito")
