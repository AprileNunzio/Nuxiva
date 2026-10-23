import asyncio
import logging
import sqlite3

import journal as journal_module
from learner import learner, name_variant
from voiceprint import Voiceprints

log = logging.getLogger("nuxiva.ear")

POLL = 45.0


def learn_name(entry: dict) -> bool:
    correction = entry["correction"]
    if not correction or learner.find_wake(entry["text"]) or not learner.find_wake(correction):
        return False
    variant = name_variant(entry["text"])
    return bool(variant) and learner.teach(variant)


def learn_voice(entry: dict, voiceprints: Voiceprints, store) -> bool:
    if not entry["fix_speaker"] or not entry["audio"] or not voiceprints.ready:
        return False
    wav = store.audio(entry["id"])
    if wav is None:
        return False
    probe = voiceprints.embed(journal_module.samples(wav))
    return probe is not None and voiceprints.add(entry["fix_speaker"], probe, "feedback") > 0


def apply_entry(entry: dict, voiceprints: Voiceprints, store) -> dict:
    if entry["verdict"] != "wrong":
        return {"name": False, "voice": False}
    return {"name": learn_name(entry), "voice": learn_voice(entry, voiceprints, store)}


def apply_pending(voiceprints: Voiceprints, store=journal_module.journal) -> int:
    done = 0
    for entry in store.pending():
        result = apply_entry(entry, voiceprints, store)
        store.mark_applied(entry["id"])
        done += 1
        if any(result.values()):
            log.info("Feedback applicato (%s): %s", entry["id"], result)
    return done


async def run(voiceprints: Voiceprints) -> None:
    while True:
        await asyncio.sleep(POLL)
        try:
            await asyncio.to_thread(apply_pending, voiceprints)
        except (OSError, sqlite3.Error, ValueError) as exc:
            log.warning("Feedback dell'ascolto non applicato: %s", exc)
