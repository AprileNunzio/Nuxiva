import json
import logging
import os
import secrets
import threading
import time

import httpx

from config import env_get
from state import store as state_store

from agenti.hands.holo.catalog import fetch, judge
from agenti.hands.holo.catalog.store import catalog
from agenti.hands.holo.forge import meshy, node

log = logging.getLogger("nuxiva.hands.holo.forge")
ERRORS = (httpx.HTTPError, fetch.FetchError, ValueError, TimeoutError, OSError, RuntimeError)
MODES = ("auto", "local", "off")
MIN_MATCH = 6
DAILY_DEFAULT = 5
LOCK = threading.Lock()


def mode() -> str:
    raw = env_get("NUXIVA_HOLO_GENERATE", "auto").strip()
    return raw if raw in MODES else "auto"


def daily_limit() -> int:
    raw = env_get("NUXIVA_HOLO_CLOUD_DAILY", str(DAILY_DEFAULT)).strip()
    return max(0, min(50, int(raw))) if raw.isdigit() else DAILY_DEFAULT


def _usage_path():
    return catalog.root / "cloud_usage.json"


def _take_cloud_slot() -> bool:
    today = time.strftime("%Y-%m-%d")
    with LOCK:
        try:
            data = json.loads(_usage_path().read_text(encoding="utf-8"))
        except (FileNotFoundError, ValueError):
            data = {}
        used = int(data.get(today, 0)) if isinstance(data, dict) else 0
        if used >= daily_limit():
            return False
        catalog.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        tmp = _usage_path().with_suffix(".tmp")
        fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump({today: used + 1}, handle)
        tmp.replace(_usage_path())
        return True


async def _local(english: str, notify) -> tuple[bytes, str, str] | None:
    if not node.url():
        return None
    notify("forge_local")
    try:
        return await node.generate(english, secrets.randbelow(2**31)), "", "local"
    except node.NodeBusy as exc:
        notify("forge_local_busy")
        log.info("nodo GPU non disponibile: %s", exc)
    except ERRORS as exc:
        notify("forge_local_busy")
        state_store.event("WARN", f"Generazione 3D sul nodo GPU non riuscita: {exc}", "holo")
    return None


async def _cloud(english: str, notify) -> tuple[bytes, str, str] | None:
    if mode() != "auto" or not meshy.token():
        return None
    if not _take_cloud_slot():
        notify("forge_cloud_limit", limit=daily_limit())
        return None
    notify("forge_cloud", stage="shape", percent=0)
    try:
        blob, thumbnail = await meshy.generate(node.prompt(english), notify)
    except ERRORS as exc:
        state_store.event("WARN", f"Generazione 3D in cloud non riuscita: {exc}", "holo")
        return None
    return blob, thumbnail, "cloud"


async def _accept(made: tuple[bytes, str, str], subject: str) -> tuple[dict, dict] | None:
    blob, thumbnail, where = made
    report = judge.inspect(blob)
    if report["score"] <= 0:
        return None
    verdict = {"match": MIN_MATCH, "quality": 5, "background": False}
    if thumbnail:
        verdict = await judge.look({"thumbnail": thumbnail}, subject)
        if verdict["match"] < MIN_MATCH:
            return None
    return report, verdict


async def create(key: str, subject: str, english: str, notify=lambda k, **p: None) -> dict | None:
    if mode() == "off":
        return None
    for attempt in (_local, _cloud):
        made = await attempt(english, notify)
        if made is None:
            continue
        try:
            accepted = await _accept(made, subject)
        except ERRORS as exc:
            log.info("modello generato non valutabile: %s", exc)
            accepted = None
        if accepted is None:
            notify("forge_rejected")
            continue
        report, verdict = accepted
        where = made[2]
        record = {"source": f"forge_{where}", "uid": secrets.token_hex(6), "name": subject[:96], "author": "Nuxiva",
                  "license": "forge_local" if where == "local" else "forge_cloud", "page": "", "animations": report["animations"],
                  "triangles": report["triangles"], "score": judge.final(report, verdict), "verdict": verdict, "reasons": report["reasons"]}
        entry = catalog.add(key, made[0], record)
        notify("forge_done", score=record["score"])
        state_store.event("INFO", f"Modello 3D di «{subject}» generato ({where}), punteggio {record['score']}", "holo")
        return entry
    return None
