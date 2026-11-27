import asyncio
import importlib
import inspect
import logging
from functools import lru_cache
from pathlib import Path

import httpx
from state import store

log = logging.getLogger("nuxiva.checkin.sources")
DEFAULT_TIMEOUT = 2.5
MAX_TIMEOUT = 5.0
MAX_FACTS = 8
KINDS = {"alert", "notice", "agenda", "interest", "info", "ok"}
REQUIRED = {"key": str, "topic": str, "kind": str, "priority": int, "signature": str, "observed_at": int, "ttl": int,
            "line": str, "params": dict}


@lru_cache(maxsize=1)
def discovered() -> tuple[tuple[str, object, float, Path], ...]:
    from feature_api_scanner import _system_agents
    found = []
    for agent in _system_agents(None):
        folder = agent.manifest_path.parent
        if not agent.module or not (folder / "briefing.py").is_file():
            continue
        try:
            module = importlib.import_module(f"{agent.module}.briefing")
        except ImportError as exc:
            log.warning("Fonte del resoconto «%s» non caricabile: %s", agent.id, exc)
            continue
        collect = getattr(module, "facts", None)
        if callable(collect):
            timeout = min(float(getattr(module, "TIMEOUT", DEFAULT_TIMEOUT)), MAX_TIMEOUT)
            found.append((agent.id, collect, timeout, folder / "language"))
    return tuple(found)


def valid(item) -> bool:
    if not isinstance(item, dict):
        return False
    if any(not isinstance(item.get(k), t) for k, t in REQUIRED.items()):
        return False
    return item["kind"] in KINDS and all(isinstance(v, str) for v in item["params"].values())


async def _run(name: str, collect, timeout: float, origin: Path) -> list[dict]:
    try:
        result = collect()
        if inspect.isawaitable(result):
            result = await asyncio.wait_for(result, timeout)
    except (asyncio.TimeoutError, httpx.HTTPError, OSError, ValueError, LookupError) as exc:
        store.event("WARN", f"Fonte del resoconto «{name}» non disponibile: {exc}", "checkin")
        return []
    items = [dict(i, origin=str(origin)) for i in (result or [])[:MAX_FACTS] if valid(i)]
    dropped = len(result or []) - len(items)
    if dropped > 0:
        store.event("WARN", f"Fonte del resoconto «{name}»: {dropped} fatti scartati perché non validi", "checkin")
    return items


async def gather() -> list[dict]:
    batches = await asyncio.gather(*(_run(*source) for source in discovered()))
    return [f for batch in batches for f in batch]
