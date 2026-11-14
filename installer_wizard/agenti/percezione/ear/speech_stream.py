import json
import logging
import time

log = logging.getLogger("nuxiva.ear.speech_stream")
TERMINATORS = ".!?…"
CLAUSE = ",;:"
ABBREVIATIONS = {"sig", "sigg", "sra", "dott", "dr", "prof", "ing", "avv", "ecc", "es", "vs", "etc", "cap", "pag", "art", "tel", "mr", "mrs", "ms", "dott.ssa", "eng", "st"}
DEFAULTS = {"min_chars": 12, "min_clause_chars": 24, "max_wait_ms": 350, "max_chunk_chars": 240, "queue_cap": 8}


def native():
    try:
        import nuxiva_native
    except ImportError:
        return None
    return getattr(nuxiva_native, "RustChunker", None)


def now_ms() -> int:
    return int(time.time() * 1000)


def _protected(text: str, at: int, rest: str) -> bool:
    token = text[:at].split()[-1] if text[:at] and not text[:at][-1].isspace() else ""
    bare = token.lstrip('("«')
    if bare.lower() in ABBREVIATIONS:
        return True
    if "." in bare and all(c.isalpha() or c == "." for c in bare):
        return True
    if len(bare) == 1:
        return bare.isupper()
    if bare and all(c in "0123456789" for c in bare):
        tail = rest.lstrip()
        return bool(tail) and (tail[0].islower() or tail[0] in "0123456789")
    return False


class PyChunker:
    def __init__(self, settings_json: str = ""):
        self._cfg = {**DEFAULTS, **(json.loads(settings_json) if settings_json else {})}
        self._buf, self._last = "", None

    def _boundary(self, last: bool):
        text = self._buf
        for i, c in enumerate(text):
            is_end, is_clause = c in TERMINATORS, c in CLAUSE
            if not is_end and not is_clause:
                continue
            end = i + 1
            if end >= len(text):
                if is_end and last:
                    return end
                continue
            if not text[end].isspace():
                continue
            if is_end:
                if c == "." and _protected(text, i, text[end:]):
                    continue
                return end
            if end >= self._cfg["min_clause_chars"]:
                return end
        return None

    def _soft(self, limit: int):
        text, best, start = self._buf, None, 0
        for i, c in enumerate(text):
            if not c.isspace():
                continue
            token = text[start:i]
            count = i + 1
            if self._cfg["min_chars"] <= count <= limit and token:
                after = text[i:].lstrip()
                prev_digit = token[-1].isdigit()
                if (not prev_digit or not (after and after[0].isdigit())) and after:
                    best = i
            start = i + 1
        return best

    def _take(self, end: int, now: int, out: list) -> None:
        chunk, self._buf = self._buf[:end].strip(), self._buf[end:].lstrip()
        if chunk:
            out.append(chunk)
        self._last = now

    def _cap(self, now: int, out: list) -> None:
        while len(self._buf) > self._cfg["max_chunk_chars"]:
            cap = self._cfg["max_chunk_chars"]
            end = self._soft(cap)
            self._take(cap if end is None else end, now, out)

    def push(self, token: str, now: int) -> list:
        if self._last is None:
            self._last = now
        self._buf += token
        out: list = []
        while (end := self._boundary(False)) is not None:
            self._take(end, now, out)
        self._cap(now, out)
        return out

    def poll(self, now: int) -> list:
        out: list = []
        waited = now - (self._last if self._last is not None else now)
        if waited >= self._cfg["max_wait_ms"] and len(self._buf) >= self._cfg["min_chars"]:
            end = self._soft(1 << 62)
            if end is not None:
                self._take(end, now, out)
        return out

    def flush(self, now: int) -> list:
        out: list = []
        while (end := self._boundary(True)) is not None:
            self._take(end, now, out)
        self._cap(now, out)
        tail, self._buf, self._last = self._buf.strip(), "", None
        if tail:
            out.append(tail)
        return out

    def reset(self) -> None:
        self._buf, self._last = "", None


def build(settings_json: str = ""):
    klass = native()
    return klass(settings_json) if klass is not None else PyChunker(settings_json)


async def stream_reply(tokens, speak, flag, chunker=None, clock=now_ms) -> int:
    chunker = chunker or build()
    spoken = 0
    async for token in tokens:
        if flag.is_cancelled():
            chunker.reset()
            return spoken
        for chunk in chunker.push(token, clock()) + chunker.poll(clock()):
            if flag.is_cancelled():
                chunker.reset()
                return spoken
            await speak(chunk)
            spoken += 1
    for chunk in chunker.flush(clock()):
        if flag.is_cancelled():
            return spoken
        await speak(chunk)
        spoken += 1
    return spoken
