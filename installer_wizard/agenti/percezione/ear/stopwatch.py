import time


class Stopwatch:

    def __init__(self) -> None:
        self.started = self.mark = time.monotonic()
        self.stages: dict = {}

    def lap(self, name: str) -> None:
        now = time.monotonic()
        self.stages[f"{name}_ms"] = int((now - self.mark) * 1000)
        self.mark = now

    def summary(self) -> dict:
        return self.stages | {"total_ms": int((time.monotonic() - self.started) * 1000)}
