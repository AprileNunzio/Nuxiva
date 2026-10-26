import asyncio
import logging
import re
import time
from dataclasses import asdict, dataclass

from config import env_get
from state import store

from features.research import extract, providers, ranking, safeweb

log = logging.getLogger("nuxiva.research")
CACHE_TTL = 600
CACHE_MAX = 128
FETCH_PARALLEL = 4
POOL = 10
SECRET = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+|\b(?:\+?\d[\d\s().-]{7,}\d)\b|\b[A-Z]{2}\d{2}[A-Z0-9]{11,30}\b|\b(?:https?://)?(?:\d{1,3}\.){3}\d{1,3}\b")
_cache: dict[tuple, tuple[float, dict]] = {}


@dataclass(slots=True)
class Source:
    title: str
    url: str
    domain: str
    reliability: str
    published: float | None
    excerpt: str
    via: str
    score: float


def scrub(question: str) -> str:
    return re.sub(r"\s+", " ", SECRET.sub(" ", question)).strip()[:200]


def language() -> str:
    return (env_get("NUXIVA_LANGUAGE", "it") or "it").strip().lower()[:2] or "it"


def enabled() -> bool:
    return env_get("NUXIVA_RESEARCH", "1") != "0"


async def _page(hit: providers.Hit, question: str, gate: asyncio.Semaphore) -> Source | None:
    host = ranking.domain_of(hit.url)
    if hit.via == "news":
        published = hit.published
        note = hit.title
    else:
        async with gate:
            try:
                page = await safeweb.fetch(hit.url, max_bytes=600_000, timeout=8)
            except safeweb.WebError as exc:
                log.info("Fonte non letta (%s): %s", exc.code, host)
                page = None
        if page is None:
            published, note = hit.published, hit.snippet
        else:
            published = extract.published_of(page.text, page.modified) or hit.published
            note = extract.excerpt(extract.readable(page.text), question) or hit.snippet
    value = ranking.score(host, published)
    return Source(hit.title, hit.url, host, ranking.label(ranking.reliability(host)), published, note[:600], hit.via, value)


def _dedupe(hits: list[providers.Hit]) -> list[providers.Hit]:
    seen: set[str] = set()
    unique = []
    for hit in hits:
        key = hit.url.split("#")[0].rstrip("/") if hit.via == "web" else hit.title.lower()
        host = ranking.domain_of(hit.url)
        if key in seen or not host or ranking.blocked(host):
            continue
        seen.add(key)
        unique.append(hit)
    return unique


async def _gather(query: str, days: int) -> tuple[list[providers.Hit], list[str]]:
    lang = language()
    jobs = [providers.news(query, lang, days), providers.duckduckgo(query, lang, days), providers.searxng(query, lang, days)]
    results = await asyncio.gather(*jobs, return_exceptions=True)
    hits: list[providers.Hit] = []
    errors: list[str] = []
    for outcome in results:
        if isinstance(outcome, safeweb.WebError):
            errors.append(outcome.code)
        elif isinstance(outcome, BaseException):
            errors.append(type(outcome).__name__)
        else:
            hits.extend(outcome)
    return hits, errors


def _setting(name: str, fallback: int, low: int, high: int) -> int:
    try:
        return max(low, min(high, int(env_get(name, str(fallback)))))
    except ValueError:
        return fallback


async def research(question: str, days: int = 0, limit: int = 5) -> dict:
    query = scrub(question)
    days = max(0, min(366, int(days))) or _setting("NUXIVA_RESEARCH_DAYS", 0, 0, 366)
    limit = max(1, min(_setting("NUXIVA_RESEARCH_MAX_SOURCES", 8, 1, 8), int(limit)))
    key = (query.lower(), days, limit)
    cached = _cache.get(key)
    if cached and time.time() - cached[0] < CACHE_TTL:
        return cached[1]
    base = {"query": query, "at": time.time(), "days": days}
    if not query or not enabled():
        return {**base, "status": "disabled" if not enabled() else "empty", "sources": [], "errors": []}
    hits, errors = await _gather(query, days)
    pool = _dedupe(hits)
    if not pool:
        status = "unavailable" if errors and len(errors) >= 2 else "no_results"
        return {**base, "status": status, "sources": [], "errors": errors}
    ranked = sorted(pool, key=lambda hit: ranking.score(ranking.domain_of(hit.url), hit.published), reverse=True)[:POOL]
    gate = asyncio.Semaphore(FETCH_PARALLEL)
    sources = [s for s in await asyncio.gather(*(_page(hit, query, gate) for hit in ranked)) if s]
    if days:
        cutoff = time.time() - days * 86400
        sources = [s for s in sources if s.published is None or s.published >= cutoff]
    sources = sorted(sources, key=lambda s: s.score, reverse=True)[:limit]
    result = {**base, "status": "ok" if sources else "no_results", "sources": [asdict(s) for s in sources], "errors": errors}
    if len(_cache) >= CACHE_MAX:
        _cache.pop(min(_cache, key=lambda k: _cache[k][0]))
    _cache[key] = (time.time(), result)
    store.event("INFO", f"Ricerca online: {len(sources)} fonti ({result['status']})", "research")
    return result
