import json
import re
import unicodedata

import native_core

MAX_INPUT = 256 * 1024
MAX_LINES = 400
MAX_TEXT = 200
MAX_WORDS = 64
MAX_WORD = 60
MAX_OFFSET_MS = 60_000
STAMP = re.compile(r"^(\d{1,3}):(\d{2})(?:[.:](\d{1,3}))?$")
OFFSET = re.compile(r"^\[\s*offset\s*:\s*([+-]?)(\d{1,6})\s*\]$", re.IGNORECASE)


def _stamp(body: str) -> int | None:
    m = STAMP.match(body)
    if not m:
        return None
    minutes, seconds, frac = m.groups()
    if int(seconds) >= 60:
        return None
    millis = int(frac) * {1: 100, 2: 10, 3: 1}[len(frac)] if frac else 0
    return int(minutes) * 60_000 + int(seconds) * 1000 + millis


def _clean(raw: str, limit: int) -> str:
    spaced = "".join(" " if unicodedata.category(c) == "Cc" else c for c in raw)
    return " ".join(spaced.split())[:limit]


def _split_words(text: str) -> tuple[str, list[tuple[int, str]]]:
    plain, words, current, buf, rest = [], [], None, [], text

    def flush():
        nonlocal buf
        chunk = "".join(buf)
        if current is not None:
            word = _clean(chunk, MAX_WORD)
            if word and len(words) < MAX_WORDS:
                words.append((current, word))
        plain.append(chunk)
        buf = []

    while (open_at := rest.find("<")) >= 0:
        buf.append(rest[:open_at])
        tail = rest[open_at:]
        close = tail.find(">")
        t = _stamp(tail[1:close]) if close > 0 else None
        if t is not None:
            flush()
            current = t
            rest = tail[close + 1:]
        else:
            buf.append("<")
            rest = tail[1:]
    buf.append(rest)
    flush()
    return _clean("".join(plain), MAX_TEXT), words


def _py_parse(raw: str) -> list[dict]:
    lines, offset = [], 0
    for row in raw[:MAX_INPUT].splitlines():
        rest, stamps = row.strip(), []
        while rest.startswith("["):
            end = rest.find("]")
            t = _stamp(rest[1:end]) if end > 0 else None
            if t is None:
                break
            stamps.append(t)
            rest = rest[end + 1:]
        if not stamps:
            m = OFFSET.match(rest)
            if m:
                offset = (-1 if m.group(1) == "-" else 1) * min(int(m.group(2)), MAX_OFFSET_MS)
            continue
        text, words = _split_words(rest)
        for t in stamps:
            lines.append({"t": t, "text": text, "words": words if len(stamps) == 1 else []})
    for line in lines:
        line["t"] = max(0, line["t"] - offset)
        line["words"] = [(max(0, t - offset), w) for t, w in line["words"]]
    lines.sort(key=lambda x: x["t"])
    return [{"t": l["t"], "text": l["text"], **({"words": [{"t": t, "text": w} for t, w in l["words"]]} if l["words"] else {})}
            for l in lines[:MAX_LINES]]


def parse_ms(raw: str) -> list[dict]:
    native = native_core.symbol("lyrics_parse")
    if native is None:
        native_core.python_fallback("music.lyrics")
        return _py_parse(str(raw or ""))
    return json.loads(native(str(raw or "")[:MAX_INPUT * 2]))


def parse(raw: str) -> list[dict]:
    out = []
    for line in parse_ms(raw):
        row = {"t": round(line["t"] / 1000, 3), "text": line["text"]}
        if line.get("words"):
            row["words"] = [{"t": round(w["t"] / 1000, 3), "text": w["text"]} for w in line["words"]]
        out.append(row)
    return out
