import json
import logging
import time

import native_module
from agenti.sentinel import record
from agenti.sentinel.journal import SentinelUnavailable
from agenti.sentinel.memory import memory

log = logging.getLogger("nuxiva.sentinel.ask")


def _engine_class():
    return native_module.feature("RustAskCore")


class AskCore:

    def __init__(self, clock=time.time) -> None:
        self.clock = clock
        self._engine = None

    def ready(self):
        if self._engine is None:
            cls = _engine_class()
            if cls is None:
                raise SentinelUnavailable("sentinel.ask.native.missing")
            self._engine = cls()
        return self._engine

    def ask(self, text: str, user: str = "household") -> dict:
        now_ms = int(self.clock() * 1000)
        try:
            engine = self.ready()
            raw_query = engine.parse(text, now_ms)
            parsed = json.loads(raw_query)
        except (SentinelUnavailable, ValueError, KeyError) as exc:
            log.warning("AskCore native parse failed or unavailable: %s", exc)
            return {
                "found": False,
                "summary": "Impossibile analizzare la richiesta.",
                "citations": [],
                "scanned": 0,
                "matched_count": 0,
            }

        search_query = {
            "from_ms": parsed.get("from_ms", now_ms - 86_400_000),
            "to_ms": parsed.get("to_ms", now_ms),
            "limit": 100,
        }
        if parsed.get("class"):
            search_query["classes"] = [parsed["class"]]

        try:
            page = memory.search(search_query)
            sightings = page.get("sightings", [])
        except Exception as exc:
            log.error("AskCore memory search failed: %s", exc)
            sightings = []

        try:
            raw_answer = engine.evaluate(json.dumps(parsed), json.dumps(sightings))
            answer = json.loads(raw_answer)
        except Exception as exc:
            log.error("AskCore evaluate failed: %s", exc)
            return {
                "found": False,
                "summary": "Errore durante l'elaborazione delle prove.",
                "citations": [],
                "scanned": len(sightings),
                "matched_count": 0,
            }

        record.record(
            "sentinel.read",
            record.NUXIVA,
            "sentinel.sentinel.ask_query",
            {
                "user": user[:40],
                "query": text[:100],
                "found": answer.get("found", False),
                "citations": len(answer.get("citations", [])),
            },
            "household",
            "sentinel",
        )

        return answer


ask_engine = AskCore()
