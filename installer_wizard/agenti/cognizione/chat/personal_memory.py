import asyncio
import logging
import os
import secrets
import threading

import native_core
from config import ETC_DIR, STATE_DIR, env_get

log = logging.getLogger("nuxiva.knowledge")
MAX_LINES = 5
_lock = threading.RLock()
_graph = None
_known: set[str] = set()


def enabled() -> bool:
    return env_get("NUXIVA_KNOWLEDGE", "off").strip().lower() == "on"


def available() -> bool:
    return native_core.symbol("RustKnowledge") is not None


def _key() -> bytes:
    path = ETC_DIR / "knowledge.key"
    if path.exists():
        data = path.read_bytes()
        if len(data) != 32:
            raise ValueError("knowledge.key")
        return data
    data = secrets.token_bytes(32)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "wb") as handle:
        handle.write(data)
    return data


def graph():
    global _graph
    with _lock:
        if _graph is None:
            from personal_graph import PersonalGraph, create_engine

            vault = STATE_DIR / "knowledge"
            _graph = PersonalGraph(create_engine(_key(), str(vault)))
        return _graph


def reset() -> None:
    global _graph
    with _lock:
        _graph = None
        _known.clear()


def _register(person: str, role: str) -> None:
    with _lock:
        if person in _known:
            return
        g = graph()
        try:
            g.call("restore", id=person)
        except Exception as exc:
            if getattr(exc, "code", "") not in ("knowledge.not_found", "knowledge.unsupported"):
                raise
        g.register(person, person, "guest" if role == "guest" else "family")
        _known.add(person)


def eligible(slug: str, role: str) -> bool:
    return bool(slug) and role != "system" and available()


def _learn(slug: str, role: str, text: str) -> None:
    _register(slug, role)
    graph().learn(slug, text, "chat")


def _recall(slug: str, role: str, text: str) -> list[str]:
    _register(slug, role)
    hits = graph().search(slug, text, limit=MAX_LINES, depth=1, min_confidence=300)
    return [h["label"] + (": " + h["detail"] if h.get("detail") else "") for h in hits]


def recall(slug: str, role: str, text: str) -> list[str]:
    if not enabled() or not eligible(slug, role):
        return []
    try:
        return _recall(slug, role, text)
    except Exception as exc:
        log.warning("Memoria personale non letta: %s", exc)
        return []


async def learn(slug: str, role: str, text: str) -> None:
    if not enabled() or not eligible(slug, role):
        return
    try:
        await asyncio.to_thread(_learn, slug, role, text)
    except Exception as exc:
        log.warning("Memoria personale non aggiornata: %s", exc)
