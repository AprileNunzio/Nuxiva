import asyncio
import re
import secrets
import time

from fastapi import Request

import setup_owner
from access import is_local
from config import DEMO
from state import store

WAKE_PREFIX = re.compile(r"^(?:hey|hei|ehi|hi|ok|okay)\s+", re.IGNORECASE)


def wake_word(assistant_name: str) -> str:
    return WAKE_PREFIX.sub("", assistant_name.strip()).strip().lower()


def _queue_voice_training(owner: dict) -> None:
    from features.chat import voice_id

    def start() -> None:
        store.voice_training = {"id": secrets.token_hex(6), "at": time.time(), **voice_id.session(owner)}
        store.touch()

    async def wait_then_start() -> None:
        from orchestrator import orch
        while orch.busy or not store.installed or store.phase not in ("READY", "DEGRADED"):
            await asyncio.sleep(2)
        start()

    if not DEMO and (not store.installed or store.phase not in ("READY", "DEGRADED")):
        from tasks import background
        background(wait_then_start())
    else:
        start()


async def complete(raw: dict, request: Request, source: str) -> dict:
    import setup_api
    first, last = setup_owner.clean_names(raw)
    updates = setup_api._clean(raw)
    voice_lang = setup_owner.clean_voice_language(raw, updates["NUXIVA_UI_LANG"])
    assistant = str(raw.get("assistant_name") or "").strip()
    if assistant:
        word = wake_word(assistant)
        updates["NUXIVA_WAKE_PHONETIC_ALIASES"] = word
    setup_api._store_cloud(raw)
    password = ""
    if raw.get("shares") is True:
        password = secrets.token_urlsafe(18)
        updates.update(NUXIVA_SMB_PASSWORD=password, NUXIVA_SHARES="1")
    await setup_api._apply(updates, source)
    owner = setup_owner.register_owner(first, last, updates["NUXIVA_UI_LANG"], voice_lang)
    setup_api._mark_done(source)
    if assistant:
        from features.ear import learner as learner_mod
        learner_mod.learner.teach(wake_word(assistant))
    training = is_local(request)
    if training:
        _queue_voice_training(owner)
    return {"ok": True, "shares_password": password, "owner": owner["slug"], "voice_training": training,
            "assistant_name": assistant or updates.get("NUXIVA_ASSISTANT_NAME", ""), "wake_word_primary": wake_word(assistant)}
