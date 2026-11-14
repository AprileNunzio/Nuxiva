import time
from pathlib import Path

from screenshot import rules, sink

MAX_FILES = 64
MAX_BYTES = 256 * 1024 * 1024
BASE_DELAY = 5
MAX_DELAY = 900


def delay(failures: int) -> int:
    return min(BASE_DELAY * (2 ** min(failures, 20)), MAX_DELAY)


class Spool:
    def __init__(self, directory: Path) -> None:
        directory.mkdir(parents=True, exist_ok=True)
        if directory.is_symlink():
            raise sink.SinkError("spool")
        self.directory = directory
        self.failures = 0
        self.next_try = 0.0

    def pending(self) -> list:
        items = [(p.name, p.stat().st_size) for p in self.directory.iterdir() if rules.is_managed(p.name) and p.is_file()]
        return sorted(items, key=lambda i: (rules.stamp(i[0]) or 0, i[0]))

    def enqueue(self, name: str, data: bytes) -> None:
        if not rules.is_managed(name) or len(data) > MAX_BYTES:
            raise sink.SinkError("name")
        while True:
            items = self.pending()
            if len(items) < MAX_FILES and sum(s for _, s in items) + len(data) <= MAX_BYTES:
                break
            (self.directory / items[0][0]).unlink()
        sink.put(self.directory, name, data)

    def flush(self, target, now: float | None = None) -> tuple:
        now = time.monotonic() if now is None else now
        delivered, failed = 0, False
        if now < self.next_try:
            return delivered, failed
        for name, _ in self.pending():
            path = self.directory / name
            try:
                target(name, path.read_bytes())
            except (sink.SinkError, OSError):
                self.failures += 1
                self.next_try = now + delay(self.failures - 1)
                failed = True
                break
            path.unlink()
            delivered += 1
            self.failures, self.next_try = 0, 0.0
        return delivered, failed

