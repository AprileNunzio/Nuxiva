import asyncio
import logging
import sqlite3

import earconf
from journal import JournalUnavailable, journal

log = logging.getLogger("nuxiva.ear")

PRUNE_EVERY = 3600.0


BROKEN = {"reason": ""}


def disable(exc: Exception) -> None:
    if not BROKEN["reason"]:
        log.warning("Registro dell'ascolto disattivato: %s", exc)
    BROKEN["reason"] = str(exc)


def journal_on() -> bool:
    return earconf.flag("NUXIVA_EAR_JOURNAL", True) and not BROKEN["reason"]


def audio_on() -> bool:
    return earconf.flag("NUXIVA_EAR_JOURNAL_AUDIO", True)


def full_text_on() -> bool:
    return earconf.flag("NUXIVA_EAR_JOURNAL_FULL", True)


async def store(report, kind: str, text: str, lang: str, speaker: str | None, score: float, woke: bool, ms: int,
                caption: dict, audio) -> None:
    if not journal_on():
        return
    try:
        await asyncio.to_thread(journal.record, kind, text, lang, speaker, score, woke, ms, caption["live"],
                                audio if audio_on() else None)
    except JournalUnavailable as exc:
        disable(exc)
    except (OSError, sqlite3.Error) as exc:
        report("registro dell'ascolto", exc)


def prune() -> int:
    return journal.prune(earconf.number("NUXIVA_EAR_JOURNAL_DAYS", 14.0, 1.0, 365.0),
                         earconf.number("NUXIVA_EAR_JOURNAL_AUDIO_DAYS", 3.0, 0.0, 60.0),
                         earconf.number("NUXIVA_EAR_JOURNAL_MAX_MB", 300.0, 20.0, 5000.0))


async def maintenance() -> None:
    while True:
        try:
            await asyncio.to_thread(prune)
        except JournalUnavailable as exc:
            disable(exc)
        except (OSError, sqlite3.Error) as exc:
            log.warning("Pulizia del registro dell'ascolto non riuscita: %s", exc)
        await asyncio.sleep(PRUNE_EVERY)
