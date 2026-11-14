import queue
import re
import threading
from typing import Callable

FIRST_LIMIT = 140
NEXT_LIMIT = 420
SENTENCE = re.compile(r"(?<=[.!?…])\s+|\n+")
_END = object()


def _wrap(sentence: str, limit: int) -> list[str]:
    pieces, current = [], ""
    for word in sentence.split():
        if current and len(current) + 1 + len(word) > limit:
            pieces.append(current)
            current = word
        else:
            current = f"{current} {word}".strip()
    if current:
        pieces.append(current)
    return pieces


def split_reply(text: str, first_limit: int = FIRST_LIMIT, next_limit: int = NEXT_LIMIT) -> list[str]:
    sentences = [p.strip() for p in SENTENCE.split(text.strip()) if p and p.strip()]
    chunks: list[str] = []
    current = ""
    for sentence in sentences:
        limit = first_limit if not chunks else next_limit
        for piece in _wrap(sentence, limit):
            if not chunks and not current:
                chunks.append(piece)
            elif current and len(current) + 1 + len(piece) > next_limit:
                chunks.append(current)
                current = piece
            else:
                current = f"{current} {piece}".strip()
    if current:
        chunks.append(current)
    return chunks


def speak_stream(chunks: list[str], fetch: Callable[[str], bytes], play: Callable[[bytes], None],
                 cancelled: threading.Event, on_first: Callable[[], None], on_error: Callable[[Exception], None],
                 errors: tuple = (Exception,)) -> bool:
    ready: queue.Queue = queue.Queue(maxsize=2)

    def produce() -> None:
        try:
            for chunk in chunks:
                if cancelled.is_set():
                    break
                ready.put(fetch(chunk))
        except errors as exc:
            ready.put(exc)
        finally:
            ready.put(_END)

    threading.Thread(target=produce, daemon=True, name="tts-prefetch").start()
    started = False
    while True:
        item = ready.get()
        if item is _END:
            return started
        if isinstance(item, Exception):
            on_error(item)
            if started:
                drain(ready)
            return started
        if cancelled.is_set():
            drain(ready)
            return started
        if not started:
            started = True
            on_first()
        play(item)


def drain(ready: queue.Queue) -> None:
    while True:
        if ready.get() is _END:
            return
