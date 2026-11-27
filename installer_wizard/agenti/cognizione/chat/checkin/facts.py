import asyncio
import logging
import time
from datetime import datetime

import httpx

from state import store

from agenti.chat.checkin.contract import fact

log = logging.getLogger("nuxiva.checkin")
SOURCE_TIMEOUT = 2.5
WARN_WINDOW = 6 * 3600
FIREWALL_WINDOW = 24 * 3600
HOT = 85
MESH_TERMS = ["server", "servers", "satelliti", "satellite", "satellites", "nodi", "nodes", "rete", "mesh"]
SYSTEM_TERMS = ["servizi", "services", "sistema", "system", "servizio", "server"]


def _ts(entry: dict) -> float:
    try:
        return datetime.fromisoformat(str(entry.get("ts", ""))).timestamp()
    except ValueError:
        return 0.0


def systems() -> list[dict]:
    comps = list((store.components or {}).values())
    down = [str(c.get("label") or "?")[:40] for c in comps if c.get("status") == "down"]
    if down:
        return [fact("systems_down", "systems", "alert", 85, 300, "systems_down",
                     {"n": len(down), "names": ", ".join(down[:3])}, terms=SYSTEM_TERMS)]
    if comps:
        return [fact("systems_ok", "systems", "ok", 30, 300, "systems_ok", {"n": len(comps)}, terms=SYSTEM_TERMS)]
    return []


def mesh() -> list[dict]:
    from agenti.nodes.registry import registry
    nodes = registry.listing()
    if not nodes:
        return []
    offline = [str(n.get("name") or "?")[:40] for n in nodes if not n.get("online")]
    if offline:
        return [fact("mesh_offline", "mesh", "alert", 75, 300, "mesh_offline",
                     {"n": len(offline), "total": len(nodes), "names": ", ".join(offline[:3])}, terms=MESH_TERMS)]
    return [fact("mesh_ok", "mesh", "ok", 30, 300, "mesh_ok", {"n": len(nodes)}, terms=MESH_TERMS)]


def warnings() -> list[dict]:
    now = time.time()
    recent = [e for e in list(store.events) if e.get("level") in ("WARN", "ERROR") and now - _ts(e) <= WARN_WINDOW]
    if not recent:
        return []
    errors = sum(1 for e in recent if e.get("level") == "ERROR")
    return [fact("warnings", "systems", "notice", 70 if errors else 45, 600, "warnings",
                 {"n": len(recent), "errors": errors}, terms=SYSTEM_TERMS)]


def resources() -> list[dict]:
    from agenti.governor.service import governor
    last = governor.last or {}
    hot = {k: last.get(k) for k in ("cpu", "mem", "temp") if isinstance(last.get(k), (int, float)) and last[k] >= HOT}
    if not hot:
        return []
    name, value = max(hot.items(), key=lambda kv: kv[1])
    return [fact("resources_hot", "systems", "notice", 60, 120, f"hot_{name}", {"value": round(value)}, terms=SYSTEM_TERMS)]


def security() -> list[dict]:
    from agenti.firewall.events import monitor
    now = time.time()
    serious = [a for a in monitor.alerts if now - a["at"] < FIREWALL_WINDOW and a.get("severity") in ("high", "critical")]
    if not serious:
        return []
    return [fact("security", "security", "alert", 80, 600, "security", {"n": len(serious)},
                 terms=["sicurezza", "security", "firewall", "attacchi"])]


def update() -> list[dict]:
    up = store.update or {}
    if not up.get("available"):
        return []
    return [fact("update", "update", "info", 40, 1800, "update", {"rev": str(up.get("target_rev") or up.get("remote_rev") or "")[:10]},
                 terms=["aggiornamento", "update", "versione"])]


async def news() -> list[dict]:
    from agenti.desktop.news import news as feed
    items = await feed.headlines()
    if not items:
        return []
    return [fact("news", "news", "info", 30, 1800, "news", {"title": items[0]["title"]}, terms=["notizie", "news", "novita"])]


SYNC = (systems, mesh, warnings, resources, security, update)
ASYNC = (news,)
IO_ERRORS = (httpx.HTTPError, asyncio.TimeoutError, OSError, ValueError)


async def _bounded(source) -> list[dict]:
    try:
        return await asyncio.wait_for(source(), SOURCE_TIMEOUT)
    except IO_ERRORS as exc:
        store.event("WARN", f"Fonte del resoconto «{source.__name__}» non disponibile: {exc}", "checkin")
        return []


def _local(source) -> list[dict]:
    try:
        return source()
    except (ImportError, AttributeError, KeyError) as exc:
        log.info("Fonte del resoconto «%s» non pronta: %s", source.__name__, exc)
        return []


async def gather() -> list[dict]:
    from agenti.chat.checkin import sources
    found = [f for source in SYNC for f in _local(source)]
    batches = await asyncio.gather(*(_bounded(s) for s in ASYNC), sources.gather())
    for batch in batches:
        found.extend(batch)
    return found
