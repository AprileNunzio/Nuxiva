import logging
import time

import httpx

from agenti.brain.brains import brains
from agenti.cloud.catalog import BY_ID, PREFIX, is_cloud
from agenti.cloud.pool import shared

log = logging.getLogger("nuxiva.chat.anticipate")

FRESH_S = 45.0
TIMEOUT = httpx.Timeout(3.0, connect=3.0)
warmed: dict[str, float] = {}


def hosts() -> list[str]:
    cfg = brains.config()
    refs = [ref for role in ("chat", "deep") for ref in cfg.get(role, []) if is_cloud(ref)]
    out: list[str] = []
    for ref in refs:
        provider = BY_ID.get(ref.removeprefix(PREFIX).partition("/")[0])
        base = (provider.base_url if provider else "").rstrip("/")
        if base.startswith("https://") and base not in out:
            out.append(base)
    return out[:4]


async def warm() -> int:
    now = time.monotonic()
    opened = 0
    for base in hosts():
        if now - warmed.get(base, -FRESH_S) < FRESH_S:
            continue
        warmed[base] = now
        try:
            await shared().head(base, timeout=TIMEOUT)
            opened += 1
        except httpx.HTTPError as exc:
            log.info("Connessione anticipata a %s non riuscita: %s", base, type(exc).__name__)
    return opened
