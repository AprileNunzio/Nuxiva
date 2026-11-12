import logging
import math
import re
import time
import unicodedata
from collections import defaultdict, deque
from dataclasses import astuple, dataclass

import native_core

from agenti.chat.history import history

KEEP = 10
STALE_SECONDS = 15 * 60
RESUME_SECONDS = 6 * 3600
RECALL_SECONDS = 24 * 3600
QUESTION_SECONDS = 60
CONTEXT_TURNS = 6
RESUME_TURNS = 4
NO_REPLY = 1e9
MAX_DEVICE = 128
MAX_TEXT_BYTES = 16_000
ELLIPSIS = re.compile(r"^\s*(?:e|ed|invece|anche|mentre)\s+(?P<rest>.{1,60}?)\s*\??\s*$", re.I)
TIME_WORDS = re.compile(r"\b(?:oggi|domani|dopodomani|stasera|stanotte|stamattina|ieri|questa settimana|"
                        r"(?:questo |il prossimo )?weekend|fine settimana|luned[iì]|marted[iì]|mercoled[iì]|"
                        r"gioved[iì]|venerd[iì]|sabato|domenica|tra \d+ giorni|la prossima settimana)\b", re.I)
PLACE = re.compile(r"\b(?:a|ad|in|per|da|su)\s+([A-ZÀ-Ý][\wÀ-ÿ'-]+(?:\s+[A-ZÀ-Ý][\wÀ-ÿ'-]+)?)")
RESUME = re.compile(r"\b(?:dove eravamo(?: rimasti)?|come dicevamo|come stavamo dicendo|riprendiamo|ricominciamo da dove|"
                    r"tornando a(?: prima| quello)?|di cosa (?:stavamo parlando|parlavamo)|continuiamo (?:il discorso|da prima)|"
                    r"il discorso di prima)\b", re.I)
SKILL_INTENTS = {"weather", "gservices", "maps", "place", "home", "action", "system", "network", "time", "music"}
log = logging.getLogger("nuxiva.chat")


@dataclass
class Turn:
    text: str
    reply: str
    intent: str
    at: float
    who: str = ""


def valid_device(device: str) -> bool:
    return bool(device) and len(device.encode("utf-8")) <= MAX_DEVICE and not any(unicodedata.category(c) == "Cc" for c in device)


def make_turn(text: str, reply: str, intent: str, at: float, who: str = "") -> Turn:
    return Turn(text[:400], reply[:600], (intent or "")[:60], at if math.isfinite(at) else 0.0, (who or "").strip()[:60])


def _lines(turns: list[Turn]) -> str:
    lines = []
    for t in turns:
        lines.append(f"{t.who or 'Utente'}: {t.text}")
        lines.append(f"Nuxiva: {t.reply[:300]}")
    return "\n".join(lines)


class PyBook:

    def __init__(self) -> None:
        self.turns: dict[str, deque] = defaultdict(lambda: deque(maxlen=KEEP))

    def knows(self, device: str) -> bool:
        return device in self.turns

    def load(self, device: str, stored: list[Turn]) -> None:
        known = {(t.text, t.at) for t in self.turns[device]}
        merged = sorted([t for t in stored if (t.text, t.at) not in known] + list(self.turns[device]), key=lambda t: t.at)
        self.turns[device] = deque(merged[-KEEP:], maxlen=KEEP)

    def remember(self, device: str, turn: Turn) -> None:
        self.turns[device].append(turn)

    def forget(self, device: str | None = None) -> None:
        if device is None:
            self.turns.clear()
        else:
            self.turns.pop(device, None)

    def within(self, device: str, now: float, window: float) -> list[Turn]:
        return [t for t in self.turns.get(device, ()) if now - t.at < window]

    def recent(self, device: str, now: float) -> list[Turn]:
        return self.within(device, now, STALE_SECONDS)

    def last(self, device: str, now: float) -> Turn | None:
        turns = self.recent(device, now)
        return turns[-1] if turns else None

    def asked_question(self, device: str, now: float) -> bool:
        last = self.last(device, now)
        return bool(last and last.reply.rstrip().endswith("?") and now - last.at < QUESTION_SECONDS)

    def since_reply(self, device: str, now: float) -> float:
        last = self.last(device, now)
        return now - last.at if last else NO_REPLY

    def context(self, device: str, now: float, query: str = "") -> str:
        recent = self.recent(device, now)
        if recent:
            return _lines(recent[-CONTEXT_TURNS:])
        older = self.within(device, now, RECALL_SECONDS if RESUME.search(query) else RESUME_SECONDS)
        if not older:
            return ""
        minutes = max(1, math.floor((now - older[-1].at) / 60 + 0.5))
        return f"Conversazione ripresa dopo {minutes} minuti. Ultimi scambi:\n" + _lines(older[-RESUME_TURNS:])

    def resolve(self, device: str, text: str, now: float) -> str:
        last = self.last(device, now)
        m = ELLIPSIS.match(text)
        if not last or not m or last.intent not in SKILL_INTENTS:
            return text
        rest = m.group("rest").strip(" ?!.")
        new_time, new_place = TIME_WORDS.search(rest), PLACE.search(rest)
        if not new_time and not new_place:
            return text
        base = last.text.rstrip(" ?!.")
        if new_time and TIME_WORDS.search(base):
            base = TIME_WORDS.sub(lambda _: new_time.group(0), base, count=1)
        elif new_time:
            base = f"{base} {new_time.group(0)}"
        if new_place and PLACE.search(base):
            base = PLACE.sub(lambda _: new_place.group(0), base, count=1)
        elif new_place:
            base = f"{base} {new_place.group(0)}"
        return base + "?"


class RustBook:

    def __init__(self, engine) -> None:
        self.engine = engine

    def knows(self, device: str) -> bool:
        return self.engine.knows(device)

    def load(self, device: str, stored: list[Turn]) -> None:
        self.engine.load(device, [astuple(t) for t in stored])

    def remember(self, device: str, turn: Turn) -> None:
        self.engine.remember(device, astuple(turn))

    def forget(self, device: str | None = None) -> None:
        self.engine.forget(device)

    def recent(self, device: str, now: float) -> list[Turn]:
        return [Turn(*row) for row in self.engine.recent(device, now)]

    def last(self, device: str, now: float) -> Turn | None:
        row = self.engine.last(device, now)
        return Turn(*row) if row else None

    def asked_question(self, device: str, now: float) -> bool:
        return self.engine.asked_question(device, now)

    def since_reply(self, device: str, now: float) -> float:
        return self.engine.since_reply(device, now)

    def context(self, device: str, now: float, query: str = "") -> str:
        return self.engine.context(device, now, query)

    def resolve(self, device: str, text: str, now: float) -> str:
        return self.engine.resolve(device, text, now)


def build_book():
    engine = native_core.symbol("RustDialogue")
    if engine is None:
        native_core.python_fallback("chat.dialogue")
        return PyBook()
    return RustBook(engine(STALE_SECONDS, RESUME_SECONDS, RECALL_SECONDS))


class Dialogue:

    def __init__(self) -> None:
        self.book = build_book()
        self.loaded: set[str] = set()

    def _load(self, device: str) -> bool:
        if not valid_device(device):
            return False
        if device in self.loaded:
            return True
        self.loaded.add(device)
        stored = [make_turn(*row) for row in history.recent(device, time.time() - RECALL_SECONDS, KEEP)]
        self.book.load(device, stored)
        return True

    def remember(self, device: str, text: str, reply: str, intent: str, who: str = "") -> None:
        turn = make_turn(text, reply, intent, time.time(), who)
        if self._load(device):
            self.book.remember(device, turn)
        history.add(device, turn.text, turn.reply, turn.intent, turn.at, turn.who)

    def forget(self, device: str | None = None) -> None:
        self.book.forget(device)
        if device is None:
            self.loaded.clear()
        elif valid_device(device):
            self.loaded.add(device)

    def recent(self, device: str) -> list[Turn]:
        return self.book.recent(device, time.time()) if self._load(device) else []

    def last(self, device: str) -> Turn | None:
        return self.book.last(device, time.time()) if self._load(device) else None

    def resolve(self, device: str, text: str) -> str:
        if len(text.encode("utf-8")) > MAX_TEXT_BYTES or not self._load(device):
            return text
        return self.book.resolve(device, text, time.time())

    def context(self, device: str, query: str = "") -> str:
        return self.book.context(device, time.time(), query[:4000]) if self._load(device) else ""

    def asked_question(self, device: str) -> bool:
        return self._load(device) and self.book.asked_question(device, time.time())

    def since_reply(self, device: str) -> float:
        return self.book.since_reply(device, time.time()) if self._load(device) else NO_REPLY


dialogue = Dialogue()
