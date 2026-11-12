import json
import logging
import os
import tempfile
import time
from datetime import date
from pathlib import Path
from typing import Callable, Iterable

log = logging.getLogger("nuxiva.widgets.novelty")

PENALTY_PER_MINUTE = 4.0
MAX_PENALTY = 35.0
SAVE_EVERY = 60.0
AUTO_CAP = 4


class Novelty:
    def __init__(self, path: Path, today: Callable[[], str] = lambda: date.today().isoformat(),
                 clock: Callable[[], float] = time.time) -> None:
        self._path = path
        self._today = today
        self._clock = clock
        self._saved_at = 0.0
        self._day, self._seen = self._load()

    def _load(self) -> tuple[str, dict]:
        try:
            raw = json.loads(self._path.read_text(encoding="utf-8"))
            if raw.get("day") == self._today() and isinstance(raw.get("seen"), dict):
                return raw["day"], raw["seen"]
        except FileNotFoundError:
            pass
        except (OSError, ValueError) as exc:
            log.warning("Widget exposure not restored (%s)", type(exc).__name__)
        return self._today(), {}

    def _rollover(self) -> None:
        today = self._today()
        if today != self._day:
            self._day, self._seen = today, {}

    def tick(self, shown: Iterable[tuple[str, str, bool]], seconds: float) -> None:
        self._rollover()
        for wid, signature, cyclic in shown:
            record = self._seen.setdefault(wid, {"seconds": 0.0, "sig": signature, "shows": 0})
            if not cyclic and record["sig"] != signature:
                record["seconds"], record["sig"] = 0.0, signature
                record["shows"] += 1
            record["seconds"] += seconds
        if self._clock() - self._saved_at >= SAVE_EVERY:
            self.save()

    def penalty(self, wid: str) -> float:
        self._rollover()
        record = self._seen.get(wid)
        return 0.0 if not record else min(MAX_PENALTY, record["seconds"] / 60.0 * PENALTY_PER_MINUTE)

    def seconds_today(self, wid: str) -> float:
        record = self._seen.get(wid)
        return 0.0 if not record else record["seconds"]

    def save(self) -> None:
        self._saved_at = self._clock()
        temporary = None
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            descriptor, temporary = tempfile.mkstemp(prefix=".novelty-", dir=self._path.parent)
            with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
                json.dump({"day": self._day, "seen": self._seen}, stream)
            os.replace(temporary, self._path)
            temporary = None
        except OSError as exc:
            log.warning("Widget exposure not saved (%s)", type(exc).__name__)
        finally:
            if temporary:
                try:
                    os.unlink(temporary)
                except OSError as exc:
                    log.warning("Temporary exposure file not removed (%s)", type(exc).__name__)
