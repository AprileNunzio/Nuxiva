import logging
import sqlite3
from typing import Any, Dict, List, Optional

from agenti.chat.interactions.store import InteractionStore, interactions

LINK_BEFORE = 180.0
LINK_AFTER = 10.0
log = logging.getLogger("nuxiva.ai_studio")


class VoiceLogUnavailable(RuntimeError):
    pass


def _journal():
    from agenti.ear.journal import journal
    return journal


def _journal_errors() -> tuple:
    from agenti.ear.journal import JournalUnavailable
    return (JournalUnavailable, sqlite3.Error, OSError)


class VoiceLogService:

    def __init__(self, store: Optional[InteractionStore] = None, journal=None) -> None:
        self.store = store or interactions
        self._journal = journal

    @property
    def journal(self):
        return self._journal or _journal()

    def _heard(self, item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        ref = item.get("voice_ref") or ""
        if not ref:
            return None
        try:
            entry = self.journal.get(ref)
        except _journal_errors() as exc:
            log.warning("Registro dell'ascolto non leggibile: %s", exc)
            return None
        if not entry or not (item["at"] - LINK_BEFORE <= entry["ts"] <= item["at"] + LINK_AFTER):
            return None
        return {key: entry[key] for key in ("text", "lang", "speaker", "score", "woke", "ms", "dur", "audio", "verdict",
                                            "correction", "note", "fix_speaker", "applied")}

    def _view(self, item: Dict[str, Any]) -> Dict[str, Any]:
        view = dict(item)
        view.pop("voice_ref", None)
        view["heard"] = self._heard(item)
        return view

    def list(self, limit: int, before: float, channel: str, query: str) -> List[Dict[str, Any]]:
        try:
            items = self.store.list(limit, before, channel, query)
        except (sqlite3.Error, OSError) as exc:
            raise VoiceLogUnavailable(str(exc)) from exc
        return [self._view(item) for item in items]

    def stats(self) -> Dict[str, Any]:
        try:
            return self.journal.stats()
        except _journal_errors() as exc:
            log.warning("Statistiche dell'ascolto non disponibili: %s", exc)
            return {}

    def _linked(self, entry_id: str) -> Optional[str]:
        item = self.store.get(entry_id)
        if not item or not self._heard(item):
            return None
        return item["voice_ref"]

    def audio(self, entry_id: str) -> Optional[bytes]:
        ref = self._linked(entry_id)
        if not ref:
            return None
        try:
            return self.journal.audio(ref)
        except _journal_errors() as exc:
            raise VoiceLogUnavailable(str(exc)) from exc

    def feedback(self, entry_id: str, verdict: str, correction: str, note: str) -> bool:
        ref = self._linked(entry_id)
        if not ref:
            return False
        try:
            return self.journal.feedback(ref, verdict, correction, "", note)
        except _journal_errors() as exc:
            raise VoiceLogUnavailable(str(exc)) from exc

    def delete(self, entry_id: str) -> bool:
        ref = self._linked(entry_id)
        if ref:
            try:
                self.journal.delete(ref)
            except _journal_errors() as exc:
                raise VoiceLogUnavailable(str(exc)) from exc
        try:
            return self.store.delete(entry_id)
        except (sqlite3.Error, OSError) as exc:
            raise VoiceLogUnavailable(str(exc)) from exc
