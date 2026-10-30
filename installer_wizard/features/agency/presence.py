import itertools
import threading
import time

from state import store

VIEWS = ("galaxy", "project", "close")
TTL_SECONDS = 30.0


class DisplayIntent:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._seq = itertools.count(1)
        self._current: dict | None = None

    def push(self, view: str, project_id: str = "") -> dict:
        if view not in VIEWS:
            raise ValueError(view)
        with self._lock:
            self._current = {"seq": next(self._seq), "view": view, "id": project_id, "at": time.time()}
            pushed = dict(self._current)
        store.touch()
        return pushed

    def current(self) -> dict | None:
        with self._lock:
            if self._current is None or time.time() - self._current["at"] > TTL_SECONDS:
                return None
            return dict(self._current)


intent = DisplayIntent()
