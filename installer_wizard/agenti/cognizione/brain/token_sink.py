from contextlib import contextmanager
from contextvars import ContextVar
from typing import Iterator, Protocol


class TokenSink(Protocol):
    def token(self, text: str) -> None: ...

    def restart(self) -> None: ...


_current: ContextVar[TokenSink | None] = ContextVar("nuxiva_brain_token_sink", default=None)


@contextmanager
def feeding(sink: TokenSink | None) -> Iterator[None]:
    marker = _current.set(sink)
    try:
        yield
    finally:
        _current.reset(marker)


def active() -> bool:
    return _current.get() is not None


def emit(text: str) -> None:
    sink = _current.get()
    if sink is not None and text:
        sink.token(text)


def restart() -> None:
    sink = _current.get()
    if sink is not None:
        sink.restart()
