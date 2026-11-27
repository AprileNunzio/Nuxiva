import asyncio
import re
import unicodedata
from collections.abc import Awaitable, Callable

MAX_KEY = 300
MAX_FLIGHTS = 64
_NOISE = re.compile(r"[^\w]+", re.UNICODE)


def key(text: str) -> str:
    folded = unicodedata.normalize("NFKC", str(text or "")).casefold()
    return " ".join(_NOISE.sub(" ", folded).split())[:MAX_KEY]


class Flight:

    def __init__(self) -> None:
        self.running: dict[str, asyncio.Task] = {}
        self.joined = 0

    async def run(self, name: str, factory: Callable[[], Awaitable]):
        task = self.running.get(name)
        if task is not None and not task.done():
            self.joined += 1
            return await asyncio.shield(task)
        if len(self.running) >= MAX_FLIGHTS:
            self.running = {k: t for k, t in self.running.items() if not t.done()}
        task = asyncio.ensure_future(factory())
        self.running[name] = task
        task.add_done_callback(lambda done, label=name: self._land(label, done))
        return await asyncio.shield(task)

    def _land(self, name: str, task: asyncio.Task) -> None:
        if self.running.get(name) is task:
            del self.running[name]
