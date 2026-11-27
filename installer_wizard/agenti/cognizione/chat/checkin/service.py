import json
import secrets
import time
from datetime import datetime

import native_core
from identity import assistant_name
from state import store

from agenti.brain import stages
from agenti.chat.checkin import compose, facts
from agenti.chat.checkin.ledger import affinity, ledger

FACTS_FRESH = 45
LLM_TIMEOUT = 12
SIMILAR = 0.75
_cache: dict = {"at": 0.0, "facts": []}
_pending: dict = {"at": 0, "told": []}
PRIVATE_KEYS = ("line", "params", "origin")


def _native(name: str):
    found = native_core.symbol(name)
    if found is None:
        native_core.python_fallback("checkin")
    return found


def detect(text: str) -> dict | None:
    probe = _native("checkin_detect")
    if probe is None:
        return None
    found = json.loads(probe(text[:600], json.dumps([assistant_name(), "Nuxiva"])))
    return found if found["phatic"] else None


async def _facts() -> list[dict]:
    if time.time() - _cache["at"] > FACTS_FRESH:
        _cache["facts"], _cache["at"] = await facts.gather(), time.time()
    return _cache["facts"]


def _plan(found: list[dict], focus: list[str], voice: bool, seed: int) -> dict:
    turns = ledger.turns()
    request = {"moment": {"now": int(time.time()), "hour": datetime.now().hour},
               "facts": [{k: v for k, v in f.items() if k not in PRIVATE_KEYS} for f in found],
               "history": [{k: t.get(k) for k in ("at", "told", "style", "humor")} for t in turns],
               "focus": focus[:8], "voice": voice, "seed": seed, "affinity": affinity.load()}
    return json.loads(_native("checkin_plan")(json.dumps(request)))


async def _write(plan: dict, by_key: dict, text: str) -> str:
    from agenti.brain.llm import BrainUnavailable, generate
    from agenti.chat import speaker
    hour = datetime.now().hour
    try:
        reply = await generate(compose.prompt(plan, by_key, speaker.instruction(), text), max_tokens=220,
                               temperature=0.7, kind="chat", timeout=LLM_TIMEOUT)
    except (BrainUnavailable, TimeoutError, ValueError) as exc:
        store.event("WARN", f"Resoconto scritto senza modello: {exc}", "checkin")
        return ""
    reply = str(reply or "").strip()
    if not reply or not compose.grounded(reply, plan, by_key, hour):
        store.event("INFO", "Bozza del resoconto scartata: cita dati non verificati", "checkin")
        return ""
    if ledger.too_similar(reply, SIMILAR):
        store.event("INFO", "Bozza del resoconto troppo simile alle ultime risposte", "checkin")
        return ""
    return speaker.fix_address(reply)


def observe(text: str, interrupted: bool = False) -> dict | None:
    if not _pending["told"]:
        return None
    learn = _native("checkin_observe")
    if learn is None:
        return None
    request = {"at": _pending["at"], "now": int(time.time()), "hour": datetime.now().hour, "reply": text[:600],
               "told": _pending["told"], "interrupted": interrupted, "affinity": affinity.load()}
    _pending["told"] = []
    learned = json.loads(learn(json.dumps(request)))
    if learned["counted"]:
        affinity.save(learned["affinity"])
        store.event("INFO", f"Resoconto: interesse per {', '.join(learned['engaged']) or 'nessun tema'}", "checkin")
    return learned


async def answer(text: str, language: str = "it", voice: bool = False) -> tuple[str, dict] | None:
    observe(text)
    found = detect(text)
    if not found:
        return None
    seed = secrets.randbits(32)
    async with stages.stage("tool", "Resoconto", "Controllo dei fatti reali"):
        current = await _facts()
        plan = _plan(current, found["focus"], voice, seed)
    by_key = {f["key"]: f for f in current}
    told = [c["signature"] for c in plan["facts"]] + [f["signature"] for f in current if f["kind"] == "ok"]
    if plan["reuse"]:
        speech = compose.unchanged(language, seed)
    else:
        async with stages.stage("system2", "Resoconto", f"{len(plan['facts'])} fatti · stile {plan['style']}"):
            speech = await _write(plan, by_key, text) or compose.fallback(plan, by_key, language)
    ledger.record(told, plan["style"], plan["humor"], speech)
    _pending["at"] = int(time.time())
    _pending["told"] = [{"topic": by_key[c["key"]]["topic"], "terms": by_key[c["key"]]["terms"]}
                        for c in plan["facts"] if c["key"] in by_key]
    return speech, {"mode": "face"}
