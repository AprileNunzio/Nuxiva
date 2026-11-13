from __future__ import annotations

import ctypes
import gc
import logging
import re
import sys
import time
from typing import Any, Callable
from urllib.parse import urlparse

import httpx

from config import OLLAMA_URL

log = logging.getLogger("nuxiva.resources.actions")

MODEL_ID = re.compile(r"^model:([A-Za-z0-9_.:/-]{1,120})$")
HEAP_EVERY = 30.0
_last_heap = 0.0


def ollama_base() -> str | None:
    parsed = urlparse(OLLAMA_URL)
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        return None
    return f"{parsed.scheme}://{parsed.netloc}"


def loaded_models(timeout: float = 2.0) -> list[dict]:
    base = ollama_base()
    if base is None:
        return []
    try:
        reply = httpx.get(f"{base}/api/ps", timeout=timeout)
        reply.raise_for_status()
        models = reply.json().get("models", [])
    except (httpx.HTTPError, ValueError) as exc:
        log.info("Modelli Ollama non letti: %s", exc)
        return []
    return [m for m in models if isinstance(m, dict) and isinstance(m.get("name"), str)][:32]


def unload_model(name: str, timeout: float = 5.0) -> bool:
    base = ollama_base()
    if base is None or not MODEL_ID.fullmatch(f"model:{name}"):
        return False
    try:
        httpx.post(f"{base}/api/generate", json={"model": name, "keep_alive": 0}, timeout=timeout).raise_for_status()
    except httpx.HTTPError as exc:
        log.warning("Scarico del modello %s non riuscito: %s", name, exc)
        return False
    return True


def release_heap(force: bool = False) -> int:
    global _last_heap
    now = time.monotonic()
    if not force and now - _last_heap < HEAP_EVERY:
        return 0
    _last_heap = now
    freed = gc.collect()
    if sys.platform.startswith("linux"):
        try:
            ctypes.CDLL("libc.so.6").malloc_trim(0)
        except (OSError, AttributeError) as exc:
            log.info("malloc_trim non disponibile: %s", exc)
    return freed


class Trimmers:
    def __init__(self) -> None:
        self.items: dict[str, tuple[Callable[[], int], Callable[[], Any]]] = {}

    def register(self, ident: str, size: Callable[[], int], trim: Callable[[], Any]) -> None:
        self.items[ident] = (size, trim)

    def components(self) -> list[dict]:
        out = []
        for ident, (size, _) in self.items.items():
            try:
                rss = max(0, int(size()))
            except (OSError, ValueError, TypeError) as exc:
                log.warning("Dimensione di %s non letta: %s", ident, exc)
                continue
            out.append({"id": f"cache.{ident}", "kind": "cache", "class": "low", "rss": rss, "idle_ms": 0,
                        "visible": False, "reclaimable": True})
        return out

    def run(self, ident: str) -> bool:
        entry = self.items.get(ident.removeprefix("cache."))
        if entry is None:
            return False
        try:
            entry[1]()
        except (OSError, ValueError, RuntimeError) as exc:
            log.warning("Pulizia di %s non riuscita: %s", ident, exc)
            return False
        return True


trimmers = Trimmers()
