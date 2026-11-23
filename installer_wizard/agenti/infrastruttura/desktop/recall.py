import hashlib
import json
import logging
import re
import time
from pathlib import Path
from typing import Callable

from sealed import write_private

log = logging.getLogger("nuxiva.secretary.recall")

LINE_TTL = 24 * 3600
CARD_TTL = 6 * 3600
MAX_LINES = 500
_DIGITS = re.compile(r"\d+")
_SPACES = re.compile(r"\s+")


def normalize(line: str) -> str:
    return _SPACES.sub(" ", _DIGITS.sub("#", str(line).casefold())).strip()[:160]


def signature(wid: str, data: dict, urgent: bool) -> str:
    lines = data.get("lines") if isinstance(data, dict) else None
    basis = [normalize(x) for x in lines] if isinstance(lines, list) else [wid, urgent]
    return hashlib.sha256(json.dumps(basis, ensure_ascii=False).encode()).hexdigest()[:24]


class Recall:
    def __init__(self, path: Path, clock: Callable[[], float] = time.time) -> None:
        self._path = path
        self._clock = clock
        self._lines: dict[str, float] = {}
        self._cards: dict[str, tuple[str, float]] = {}
        self._load()

    def _load(self) -> None:
        try:
            raw = json.loads(self._path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return
        except (OSError, ValueError) as exc:
            log.warning("Memoria dei widget già visti non ripristinata (%s)", type(exc).__name__)
            return
        if isinstance(raw, dict):
            self._lines = {str(k): float(v) for k, v in (raw.get("lines") or {}).items() if isinstance(v, (int, float))}
            self._cards = {str(k): (str(v[0]), float(v[1])) for k, v in (raw.get("cards") or {}).items()
                           if isinstance(v, list) and len(v) == 2 and isinstance(v[1], (int, float))}
        self._expire()

    def _expire(self) -> None:
        now = self._clock()
        self._lines = {k: v for k, v in self._lines.items() if now - v < LINE_TTL}
        self._cards = {k: v for k, v in self._cards.items() if now - v[1] < CARD_TTL}

    def known_lines(self) -> frozenset[str]:
        self._expire()
        return frozenset(self._lines)

    def seen_card(self, name: str, sig: str) -> bool:
        self._expire()
        return self._cards.get(name, ("", 0.0))[0] == sig

    def mark(self, name: str, sig: str, lines: list | None = None) -> None:
        now = self._clock()
        self._cards[name] = (sig, now)
        for line in lines or []:
            self._lines[normalize(line)] = now
        if len(self._lines) > MAX_LINES:
            self._lines = dict(sorted(self._lines.items(), key=lambda kv: kv[1])[-MAX_LINES:])
        self.save()

    def save(self) -> None:
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            payload = {"lines": self._lines, "cards": {k: [v[0], v[1]] for k, v in self._cards.items()}}
            write_private(self._path, json.dumps(payload, ensure_ascii=False).encode())
        except OSError as exc:
            log.warning("Memoria dei widget già visti non salvata (%s)", type(exc).__name__)
