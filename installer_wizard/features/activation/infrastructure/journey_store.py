from __future__ import annotations

import json
import os
import time
from pathlib import Path

from features.activation.domain.errors import JourneyError
from features.activation.domain.journey import Journey


class JourneyStore:
    def __init__(self, path: Path) -> None:
        self._path = path

    def exists(self) -> bool:
        return self._path.exists()

    def load(self) -> Journey | None:
        if not self._path.exists():
            return None
        try:
            raw = json.loads(self._path.read_text(encoding="utf-8"))
            return Journey.from_dict(raw)
        except (OSError, ValueError, JourneyError):
            return None

    def save(self, journey: Journey) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self._path.with_suffix(f".tmp.{os.getpid()}.{time.time_ns()}")
        payload = json.dumps(journey.to_dict(), indent=2, ensure_ascii=False)
        try:
            tmp.write_text(payload, encoding="utf-8")
            with tmp.open("r+", encoding="utf-8") as f:
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp, self._path)
        except OSError as exc:
            if tmp.exists():
                tmp.unlink(missing_ok=True)
            raise JourneyError("journey.store_write_failed", error=str(exc)) from exc

    def wipe(self) -> None:
        self._path.unlink(missing_ok=True)
