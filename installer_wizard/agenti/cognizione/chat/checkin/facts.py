import asyncio
import hashlib
import json
import logging
import time
from datetime import datetime, timedelta, timezone

import httpx

from state import store

log = logging.getLogger("nuxiva.checkin")
SOURCE_TIMEOUT = 2.5
WARN_WINDOW = 6 * 3600
FIREWALL_WINDOW = 24 * 3600
HOT = 85
MESH_TERMS = ["server", "servers", "satelliti", "satellite", "satellites", "nodi", "nodes", "rete", "mesh"]
SYSTEM_TERMS = ["servizi", "services", "sistema", "system", "servizio", "server"]


def fact(key: str, topic: str, kind: str, priority: int, ttl: int, line: str, params: dict | None = None,
         starts_at: float | None = None, terms: list[str] | None = None) -> dict:
    params = {k: str(v)[:120] for k, v in (params or {}).items()}
    raw = json.dumps([key, line, params], sort_keys=True, ensure_ascii=False)
    return {"key": key, "topic": topic, "kind": kind, "priority": max(0, min(100, int(priority))),
            "signature": hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32], "observed_at": int(time.time()),
            "ttl": int(ttl), "starts_at": int(starts_at) if starts_at else None, "terms": (terms or [])[:16],
            "line": line, "params": params}


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


def _profile() -> dict | None:
    from agenti.chat import context as request_context
    from agenti.people import identity
    return identity.current(request_context.voice.get()) or identity.owner()


def _start(match: dict) -> float | None:
    try:
        return datetime.fromisoformat(match["start"].replace("Z", "+00:00")).timestamp()
    except (KeyError, ValueError):
        return None


async def sports() -> list[dict]:
    from agenti.sports.prefs import HOUSEHOLD, prefs
    from agenti.sports.spotlight import team_card
    profile = _profile()
    teams = (prefs.get(profile["slug"]) if profile else {}).get("teams") or prefs.get(HOUSEHOLD).get("teams") or []
    cards = await asyncio.gather(*(team_card(t) for t in teams[:3]))
    out = []
    for card in (c for c in cards if c and c["kind"] in ("live", "today", "result")):
        m, team = card["match"], card["team"]
        rival = m["away"] if m["home"]["id"] == team["id"] else m["home"]
        at = _start(m)
        local = datetime.fromtimestamp(at).strftime("%H:%M") if at else ""
        score = f"{m['home'].get('score') or 0}-{m['away'].get('score') or 0}"
        priority = {"live": 75, "today": 60, "result": 45}[card["kind"]]
        out.append(fact(f"sport_{team['id']}", "sport", "interest", priority, 900, f"sport_{card['kind']}",
                        {"team": team["name"], "rival": rival.get("name", ""), "time": local, "score": score},
                        starts_at=at, terms=["partita", "match", "calcio", "football", team["name"]]))
    return out


async def mail() -> list[dict]:
    from agenti.google.commands import _context
    from agenti.google.constants import NotLinked
    try:
        ctx = _context("gmail", True)
    except (LookupError, NotLinked):
        return []
    unread = await ctx.session.unread_threads(-1)
    if unread < 0:
        return []
    if not unread:
        return [fact("mail_none", "email", "ok", 25, 600, "mail_none", terms=["email", "mail", "posta"])]
    return [fact("mail_unread", "email", "notice", 50 if unread < 10 else 55, 600, "mail_unread", {"n": unread},
                 terms=["email", "mail", "posta"])]


async def agenda() -> list[dict]:
    from agenti.google.commands import _context
    from agenti.google.constants import NotLinked
    try:
        ctx = _context("calendar", True)
    except (LookupError, NotLinked):
        return []
    now = datetime.now(timezone.utc)
    events = await ctx.session.events(now, now + timedelta(hours=12), 3)
    out = []
    for e in events[:2]:
        try:
            at = datetime.fromisoformat(str(e["start"]).replace("Z", "+00:00")).timestamp()
        except ValueError:
            at = None
        when = datetime.fromtimestamp(at).strftime("%H:%M") if at and not e.get("all_day") else ""
        out.append(fact(f"agenda_{hashlib.sha256(str(e.get('title')).encode()).hexdigest()[:8]}", "agenda", "agenda", 60, 900,
                        "agenda", {"title": str(e.get("title") or "")[:80], "time": when}, starts_at=at,
                        terms=["agenda", "impegni", "calendario", "appuntamenti"]))
    return out


SYNC = (systems, mesh, warnings, resources, security, update)
ASYNC = (news, sports, mail, agenda)
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
    found = [f for source in SYNC for f in _local(source)]
    for batch in await asyncio.gather(*(_bounded(s) for s in ASYNC)):
        found.extend(batch)
    return found
