import asyncio
import time
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any, Dict, Iterator, List, Optional, Tuple

OPEN_TAG = "<thought>"
CLOSE_TAG = "</thought>"


def _partial_suffix(text: str, tag: str) -> int:
    for size in range(min(len(text), len(tag) - 1), 0, -1):
        if tag.startswith(text[-size:]):
            return size
    return 0


class ThoughtSplitter:
    def __init__(self) -> None:
        self.in_thought = False
        self.pending = ""

    def feed(self, text: str) -> List[Tuple[str, str]]:
        out: List[Tuple[str, str]] = []
        buf = self.pending + text
        while buf:
            tag = CLOSE_TAG if self.in_thought else OPEN_TAG
            idx = buf.find(tag)
            if idx >= 0:
                if idx:
                    out.append((self.kind, buf[:idx]))
                buf = buf[idx + len(tag):]
                self.in_thought = not self.in_thought
                continue
            keep = _partial_suffix(buf, tag)
            if len(buf) > keep:
                out.append((self.kind, buf[:len(buf) - keep]))
            buf = buf[len(buf) - keep:]
            break
        self.pending = buf
        return out

    def flush(self) -> List[Tuple[str, str]]:
        rest, self.pending = self.pending, ""
        return [(self.kind, rest)] if rest else []

    @property
    def kind(self) -> str:
        return "thought_delta" if self.in_thought else "token"


class StreamRelay:
    def __init__(self, queue: "asyncio.Queue[Dict[str, Any]]", clock=time.perf_counter) -> None:
        self.queue = queue
        self.clock = clock
        self.splitter = ThoughtSplitter()
        self.thought_started: Optional[float] = None
        self.thought_ended: Optional[float] = None

    def token(self, text: str) -> None:
        self._push(self.splitter.feed(text))

    def restart(self) -> None:
        self.splitter = ThoughtSplitter()
        self.thought_started = self.thought_ended = None
        self.queue.put_nowait({"type": "reset"})

    def close(self) -> None:
        self._push(self.splitter.flush())

    def thinking_ms(self) -> int:
        if self.thought_started is None:
            return 0
        end = self.thought_ended if self.thought_ended is not None else self.clock()
        return max(0, int((end - self.thought_started) * 1000))

    def _push(self, events: List[Tuple[str, str]]) -> None:
        for kind, text in events:
            now = self.clock()
            if kind == "thought_delta" and self.thought_started is None:
                self.thought_started = now
            if kind == "token" and self.thought_started is not None and self.thought_ended is None and text.strip():
                self.thought_ended = now
            self.queue.put_nowait({"type": kind, "token": text})


_listener: ContextVar[Optional[StreamRelay]] = ContextVar("nuxiva_studio_listener", default=None)


@contextmanager
def listening(relay: StreamRelay) -> Iterator[None]:
    marker = _listener.set(relay)
    try:
        yield
    finally:
        _listener.reset(marker)


def listener() -> Optional[StreamRelay]:
    return _listener.get()
