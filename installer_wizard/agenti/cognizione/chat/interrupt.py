import json
import logging
import threading
import time
import uuid
from collections import OrderedDict

log = logging.getLogger("nuxiva.chat.interrupt")

TTL_SECONDS = 180.0
MAX_ENTRIES = 32
MAX_TEXT = 8192
MAX_DEVICE = 64
_lock = threading.Lock()
_entries: "OrderedDict[str, dict]" = OrderedDict()


def _merge():
    from agenti.ear import merge
    return merge.build()


def _clean(text: str) -> str:
    return "".join(ch for ch in str(text or "") if ch.isprintable() or ch in "\n\t")[:MAX_TEXT]


def remember(device: str, spoken: str, unspoken: str, now: float | None = None) -> str:
    key, moment = str(device or "")[:MAX_DEVICE], time.time() if now is None else now
    ref = "ir-" + uuid.uuid4().hex[:16]
    with _lock:
        _entries[key] = {"ref": ref, "spoken": _clean(spoken), "unspoken": _clean(unspoken), "at": moment}
        _entries.move_to_end(key)
        while len(_entries) > MAX_ENTRIES:
            _entries.popitem(last=False)
    return ref


def _take(device: str, now: float) -> dict | None:
    key = str(device or "")[:MAX_DEVICE]
    with _lock:
        entry = _entries.pop(key, None)
    if entry is None or now - entry["at"] > TTL_SECONDS:
        return None
    return entry


def pending(device: str, now: float | None = None) -> bool:
    entry = _entries.get(str(device or "")[:MAX_DEVICE])
    return entry is not None and (time.time() if now is None else now) - entry["at"] <= TTL_SECONDS


def _plan(entry: dict, text: str) -> dict | None:
    engine = _merge()
    note = json.dumps({"spoken_text": entry["spoken"], "unspoken_ref": entry["ref"], "interrupted_at_ms": 0, "spoken_chars": len(entry["spoken"])})
    try:
        return json.loads(engine.plan(note, text))
    except ValueError as exc:
        log.warning("piano di ripresa rifiutato: %s", exc)
        return None


def context_for(device: str, text: str, now: float | None = None) -> str:
    moment = time.time() if now is None else now
    entry = _take(device, moment)
    if entry is None:
        return ""
    plan = _plan(entry, _clean(text)[:512])
    if plan is None:
        return ""
    intent = plan["intent"]
    if intent == "continue":
        return ("Sei stata interrotta e ora ti chiedono di proseguire: riprendi esattamente da qui senza ripetere ciò che hai già detto. "
                f"Già detto: «{entry['spoken'][-400:]}». Parte non ancora detta: «{entry['unspoken']}».")
    if intent == "modify":
        return ("Sei stata interrotta e ora ti chiedono di rifare la risposta con una correzione: rifalla tenendone conto. "
                f"Già detto: «{entry['spoken'][-400:]}». Parte non ancora detta: «{entry['unspoken'][:600]}».")
    if intent == "cancel":
        return "Sei stata interrotta e ora ti dicono di lasciar stare: non riprendere la risposta precedente, conferma brevemente."
    return ""


def clear() -> None:
    with _lock:
        _entries.clear()
