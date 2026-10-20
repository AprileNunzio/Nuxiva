from collections.abc import Awaitable, Callable
from contextvars import ContextVar

import httpx

from features.brain.free_router import capability_matrix, catalog_poller, rate_limiter, telemetry_emitter

POOL_BY_MODEL: dict[str, str] = {}
_last_failure: ContextVar[dict | None] = ContextVar("free_router_last_failure", default=None)


async def free_refs(pool: str, metrics: dict | None = None) -> list[str]:
    models = await catalog_poller.refresh()
    eligible = capability_matrix.candidates(models, pool, metrics)
    references = []
    for model in eligible:
        if rate_limiter.rate_limiter.available("openrouter", model["id"]):
            POOL_BY_MODEL[model["id"]] = pool
            references.append(f"cloud:openrouter/{model['id']}")
    return references


async def configured_refs(pool: str) -> list[str] | None:
    from features.brain.free_router import settings
    configured = settings.load()
    if not configured["enabled"] or pool not in configured["pools"]:
        return None
    from features.cloud.vault import vault
    if not vault.configured("openrouter"):
        return []
    try:
        return await free_refs(pool)
    except (httpx.HTTPError, ValueError, OSError):
        return []


def pool_for(ref: str, fallback: str = "chat") -> str:
    return POOL_BY_MODEL.get(ref.removeprefix("cloud:openrouter/"), fallback)


def observe(ref: str, headers: dict[str, str], status: int, elapsed_ms: float = 0.0, now: float | None = None) -> None:
    if not ref.startswith("cloud:openrouter/"):
        return
    model = ref.removeprefix("cloud:openrouter/")
    rate = rate_limiter.rate_limiter.observe("openrouter", model, headers, status, now)
    if elapsed_ms > 0 and status < 400:
        rate.ttft_ms = elapsed_ms
    if status in (401, 403, 429) or status >= 500:
        _last_failure.set({"id": model, "name": model})


def failed(ref: str, status: int, headers: dict[str, str] | None = None, now: float | None = None) -> None:
    if not ref.startswith("cloud:openrouter/"):
        return
    rate_limiter.rate_limiter.observe("openrouter", ref.removeprefix("cloud:openrouter/"), headers or {}, status, now)
    _last_failure.set({"id": ref.removeprefix("cloud:openrouter/"), "name": ref.removeprefix("cloud:openrouter/")})


def succeeded(ref: str, name: str = "", elapsed_ms: float = 0.0, pool: str = "chat") -> None:
    if ref.startswith("cloud:openrouter/"):
        model_id = ref.removeprefix("cloud:openrouter/")
        previous = _last_failure.get()
        _last_failure.set(None)
        if previous and previous.get("id") == model_id:
            previous = None
        telemetry_emitter.emit("READY", {"id": model_id, "name": name or model_id, "pool": pool}, previous)


async def run(candidates: list[dict], pool: str, call: Callable[[dict], Awaitable[object]]) -> object:
    eligible = capability_matrix.candidates(candidates, pool, rate_limiter.rate_limiter.metrics())
    errors = []
    previous = None
    for candidate in eligible:
        model_id = candidate["id"]
        if not rate_limiter.rate_limiter.available("openrouter", model_id):
            continue
        try:
            result = await call(candidate)
        except Exception as exc:
            status = getattr(exc, "status_code", None)
            if status is None and isinstance(exc, (ConnectionError, httpx.TimeoutException, httpx.NetworkError)):
                status = 503
            if status is None:
                raise
            failed(f"cloud:openrouter/{model_id}", int(status), getattr(exc, "headers", {}))
            telemetry_emitter.emit("FAILOVER", candidate, previous, "free_router.failover_reason.rate_limit_429" if status == 429 else "free_router.failover_reason.provider_error")
            errors.append(f"{model_id}:{status}")
            previous = candidate
            continue
        succeeded(f"cloud:openrouter/{model_id}", candidate.get("name", ""), pool=pool)
        return result
    raise RuntimeError("free_router.no_eligible_model" if not errors else "free_router.all_candidates_failed")
