import asyncio
import contextlib
import contextvars
import json
import logging
import threading
import time

import httpx
from config import STATE_DIR

log = logging.getLogger("nuxiva.sports")
ALLOWED_HOSTS = ("https://site.api.espn.com/", "https://api.jolpi.ca/")
DIGEST_PATH = STATE_DIR / "sports_digest.json"
MAX_ENTRIES = 256
MAX_DIGEST = 400
_cache: dict[str, tuple[float, dict]] = {}
_locks: dict[str, asyncio.Lock] = {}
_capture: contextvars.ContextVar[float | None] = contextvars.ContextVar("sports_capture", default=None)
_guard = threading.Lock()
_state: dict | None = None


class SportsUnavailable(RuntimeError):
    pass


def _load() -> dict:
    global _state
    if _state is None:
        try:
            raw = json.loads(DIGEST_PATH.read_text(encoding="utf-8"))
        except (FileNotFoundError, ValueError, OSError):
            raw = {}
        entries = raw.get("entries") if isinstance(raw, dict) else None
        _state = {"built": str(raw.get("built") or "") if isinstance(raw, dict) else "",
                  "entries": {k: v for k, v in (entries or {}).items()
                              if isinstance(v, dict) and isinstance(v.get("data"), dict) and k.startswith(ALLOWED_HOSTS)}}
    return _state


def _save() -> None:
    with _guard:
        tmp = DIGEST_PATH.with_suffix(".tmp")
        tmp.write_text(json.dumps(_load(), ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        tmp.replace(DIGEST_PATH)


def _remember(url: str, data: dict, until: float) -> None:
    entries = _load()["entries"]
    entries[url] = {"at": time.time(), "until": until, "data": data}
    while len(entries) > MAX_DIGEST:
        entries.pop(min(entries, key=lambda k: entries[k]["at"]))


@contextlib.contextmanager
def capture(until: float):
    token = _capture.set(until)
    try:
        yield
    finally:
        _capture.reset(token)


def retime(prefixes: tuple[str, ...], until: float) -> None:
    for url, entry in _load()["entries"].items():
        if url.startswith(prefixes):
            entry["until"] = until


def commit(built: str | None = None) -> None:
    if built is not None:
        _load()["built"] = built
    _save()


def reset() -> None:
    _load()["entries"].clear()
    _cache.clear()
    commit("")


def status() -> dict:
    state = _load()
    now = time.time()
    entries = state["entries"].values()
    return {"built": state["built"], "entries": len(state["entries"]),
            "fresh": sum(1 for e in entries if e["until"] > now), "oldest": min((e["at"] for e in entries), default=0)}


def built_day() -> str:
    return _load()["built"]


def _from_digest(url: str) -> dict | None:
    entry = _load()["entries"].get(url)
    return entry["data"] if entry and entry["until"] > time.time() else None


def _stale(url: str) -> dict | None:
    entry = _load()["entries"].get(url)
    return entry["data"] if entry else None


async def get_json(url: str, ttl: float) -> dict:
    if not url.startswith(ALLOWED_HOSTS):
        raise SportsUnavailable("fonte non ammessa")
    until = _capture.get()
    hit = _cache.get(url)
    if until is None:
        if hit and time.time() - hit[0] < ttl:
            return hit[1]
        known = _from_digest(url)
        if known is not None:
            return known
    lock = _locks.setdefault(url, asyncio.Lock())
    async with lock:
        hit = _cache.get(url)
        if until is None and hit and time.time() - hit[0] < ttl:
            return hit[1]
        try:
            async with httpx.AsyncClient(timeout=10, headers={"User-Agent": "Nuxiva-OS"}, follow_redirects=False) as client:
                res = await client.get(url)
            res.raise_for_status()
            data = res.json()
        except (httpx.HTTPError, ValueError) as exc:
            fallback = hit[1] if hit else _stale(url)
            if fallback is not None:
                return fallback
            raise SportsUnavailable(f"servizio sportivo non raggiungibile ({type(exc).__name__})") from exc
        data = data if isinstance(data, dict) else {}
        if len(_cache) >= MAX_ENTRIES:
            oldest = min(_cache, key=lambda k: _cache[k][0])
            _cache.pop(oldest)
            if oldest != url and not _locks.get(oldest, lock).locked():
                _locks.pop(oldest, None)
        _cache[url] = (time.time(), data)
        if until is not None:
            _remember(url, data, until)
        return data
