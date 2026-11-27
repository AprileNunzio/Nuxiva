import time
from collections import deque


class Budget:

    def __init__(self, per_minute: int, clock=time.monotonic) -> None:
        self.per_minute = per_minute
        self.clock = clock
        self.spent: dict[str, deque] = {}

    def take(self, who: str) -> bool:
        now = self.clock()
        window = self.spent.setdefault(who[:80], deque())
        while window and now - window[0] >= 60.0:
            window.popleft()
        if len(window) >= self.per_minute:
            return False
        window.append(now)
        if len(self.spent) > 256:
            self.spent = {k: v for k, v in self.spent.items() if v}
        return True
