import asyncio
import json
import re
import time
from typing import Any

import httpx
from config import ollama_url
from tasks import background

from features.brain import scope
from features.brain.assignments import load_synaptic_weights, save_synaptic_weights
from features.brain.brains import brains
from features.brain.trace import trace
from features.brain.residency import keep_alive, touch
from features.cloud.catalog import is_cloud
from features.cloud.client import CloudError, complete

_FENCE = re.compile(r"^```(?:json)?\s*|\s*```$", re.I)


class BrainUnavailable(RuntimeError):
    pass


async def chain(kind: str = "deep") -> list[str]:
    cfg = brains.config()
    installed = {n if ":" in n else f"{n}:latest" for n in await brains.installed()}
    order = brains.effective(kind, cfg, cfg["deep" if kind == "chat" else "chat"])
    usable = [m for m in dict.fromkeys(order) if brains.usable(m, installed)]
    return usable or [cfg["main"]]


async def component_chain(component: str) -> list[str]:
    if not component:
        return []
    from features.brain.routing import assignment_service
    installed = {n if ":" in n else f"{n}:latest" for n in await brains.installed()}
    return assignment_service.chain(component, installed)


def decode(text: str, as_json: bool):
    if not as_json:
        return text.strip()
    body = _FENCE.sub("", text.strip())
    start, end = body.find("{"), body.rfind("}")
    return json.loads(body[start:end + 1] if start >= 0 and end > start else body)


async def _ollama(model: str, prompt: str, system: str, as_json: bool, max_tokens: int, temperature: float,
                  timeout: float) -> str:
    body = {"model": model, "prompt": prompt, "stream": False, "keep_alive": keep_alive(model),
            "options": {"temperature": temperature, "num_predict": max_tokens}}
    if system:
        body["system"] = system
    if as_json:
        body["format"] = "json"
    async with httpx.AsyncClient(timeout=httpx.Timeout(timeout, connect=10)) as client:
        r = await client.post(f"{ollama_url()}/api/generate", json=body)
        r.raise_for_status()
    return r.json().get("response", "")


def _govern(system: str) -> str:
    try:
        from features.laws.laws import laws
        preamble = laws.preamble()
    except Exception:
        preamble = ""
    return (preamble + "\n\n" + system) if preamble else system


async def generate(prompt: str, *, as_json: bool = False, max_tokens: int = 500, temperature: float = 0.1,
                   kind: str = "deep", system: str = "", prefer: list[str] | None = None, timeout: float = 240,
                   govern: bool = True, component: str = ""):
    if component:
        from features.brain.routing import assignment_service
        tuned = assignment_service.tuning(component)
        temperature = tuned.temperature if tuned.temperature is not None else temperature
        max_tokens = tuned.max_tokens if tuned.max_tokens is not None else max_tokens
        timeout = tuned.timeout if tuned.timeout is not None else timeout
        system = tuned.system(system)
    if govern:
        system = _govern(system)
    errors = []
    models = list(dict.fromkeys([m for m in prefer or [] if m] + await component_chain(component) + await chain(kind)))
    pool = "agent_tools" if as_json else "deep_code" if kind == "deep" else "chat"
    from features.brain.free_router.failover_engine import configured_refs, pool_for, succeeded
    free_models = await configured_refs(pool)
    free_matrix_active = free_models is not None
    if free_matrix_active:
        local_models = [model for model in models if scope.origin(model) != scope.CLOUD]
        models = list(dict.fromkeys([*free_models, *local_models]))
    call = trace.begin(component or kind, "richiesta di ragionamento" if kind == "deep" else "richiesta veloce", models)
    for model in models:
        if free_matrix_active and model.startswith("cloud:openrouter/"):
            from features.brain.free_router.rate_limiter import rate_limiter
            if not rate_limiter.available("openrouter", model.removeprefix("cloud:openrouter/")):
                continue
        trace.attempt(call, model)
        started = time.perf_counter()
        try:
            if is_cloud(model):
                reply = await complete(model, [{"role": "user", "content": prompt}], system, max_tokens=max_tokens,
                                       temperature=temperature, json_mode=as_json)
                text = reply.text
            else:
                text = await _ollama(model, prompt, system, as_json, max_tokens, temperature, timeout)
            result = decode(text, as_json)
        except (httpx.HTTPError, CloudError, ValueError) as exc:
            errors.append(f"{model}: {str(exc)[:120]}")
            trace.failed(call, model, str(exc) or type(exc).__name__)
            brains.record(model, (time.perf_counter() - started) * 1000, False, kind)
            if component:
                try:
                    sw = load_synaptic_weights()
                    key = f"{component}:{model}"
                    sw[key] = max(0.05, round(sw.get(key, 0.6) - 0.05, 3))
                    save_synaptic_weights(sw)
                except Exception:
                    pass
            continue
        elapsed = (time.perf_counter() - started) * 1000
        if free_matrix_active and model.startswith("cloud:openrouter/"):
            succeeded(model, model.removeprefix("cloud:openrouter/"), elapsed, pool_for(model, pool))
        brains.record(model, elapsed, True, kind)
        trace.finish(call, model, elapsed, text)
        background(touch(model))
        if component:
            try:
                sw = load_synaptic_weights()
                key = f"{component}:{model}"
                sw[key] = min(2.5, round(sw.get(key, 0.6) + 0.05, 3))
                save_synaptic_weights(sw)
            except Exception:
                pass
        return result
    trace.abort(call, "; ".join(errors))
    raise BrainUnavailable("; ".join(errors) or "nessun modello disponibile")


async def generate_branches(
    prompt: str,
    *,
    n_branches: int = 1,
    as_json: bool = False,
    max_tokens: int = 500,
    temperature: float = 0.1,
    kind: str = "deep",
    system: str = "",
    prefer: list[str] | None = None,
    timeout: float = 240,
    govern: bool = True,
    component: str = "",
) -> list[Any]:
    if n_branches <= 1:
        single = await generate(
            prompt,
            as_json=as_json,
            max_tokens=max_tokens,
            temperature=temperature,
            kind=kind,
            system=system,
            prefer=prefer,
            timeout=timeout,
            govern=govern,
            component=component,
        )
        return [single]
    tasks = [
        asyncio.create_task(
            generate(
                prompt,
                as_json=as_json,
                max_tokens=max_tokens,
                temperature=min(1.0, max(0.05, temperature + (i * 0.07))),
                kind=kind,
                system=system,
                prefer=prefer,
                timeout=timeout,
                govern=govern,
                component=component,
            )
        )
        for i in range(min(n_branches, 8))
    ]
    done, pending = await asyncio.wait(tasks, timeout=timeout)
    for p in pending:
        p.cancel()
    results = []
    for d in done:
        try:
            results.append(d.result())
        except Exception:
            pass
    if not results:
        raise BrainUnavailable("nessuna branca parallela completata")
    return results
