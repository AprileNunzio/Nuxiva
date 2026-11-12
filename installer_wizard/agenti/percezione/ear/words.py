import time
from collections import deque
from dataclasses import dataclass, field

import native_core

LEXICON_TTL = 60.0
RECENT_SECONDS = 120.0
RECENT_KEEP = 6
PROMPT_SECONDS = 60.0
PROMPT_CHARS = 200
MAX_TERMS = 400
MAX_WORDS = 512


@dataclass(frozen=True, slots=True)
class Heard:
    text: str
    confidence: float
    fixes: tuple = ()
    dropped: tuple = ()
    words: list = field(default_factory=list, compare=False)


class WordFixer:

    def __init__(self, terms=None, clock=time.time) -> None:
        self.lexicon_cls = native_core.symbol("RustLexicon")
        self.assess_fn = native_core.symbol("ear_assess_segments")
        if self.lexicon_cls is None or self.assess_fn is None:
            native_core.python_fallback("ear.words")
        self.terms = terms
        self.clock = clock
        self.lexicon = None
        self.lexicon_key: tuple = ()
        self.lexicon_at = 0.0
        self.recent: deque = deque(maxlen=RECENT_KEEP)

    @property
    def native(self) -> bool:
        return self.lexicon_cls is not None and self.assess_fn is not None

    def _lexicon(self):
        now = self.clock()
        if self.lexicon is not None and now - self.lexicon_at < LEXICON_TTL:
            return self.lexicon
        terms = tuple(str(t) for t in (self.terms() if self.terms else ())[:MAX_TERMS] if t)
        if self.lexicon is None or terms != self.lexicon_key:
            self.lexicon = self.lexicon_cls(list(terms))
            self.lexicon_key = terms
        self.lexicon_at = now
        return self.lexicon

    def context(self) -> list[str]:
        now = self.clock()
        return [w for at, text in self.recent if now - at < RECENT_SECONDS for w in text.split()][:256]

    def prompt_tail(self) -> str:
        now = self.clock()
        last = next(((at, text) for at, text in reversed(self.recent)), None)
        if not last or now - last[0] >= PROMPT_SECONDS:
            return ""
        return last[1][-PROMPT_CHARS:]

    def remember(self, text: str) -> None:
        if text:
            self.recent.append((self.clock(), text[:400]))

    def hear(self, segments: list, prompt: str, phrases: set[str]) -> Heard:
        if not self.native:
            return _py_hear(segments, phrases)
        rows = [(_text(s), _num(s, "avg_logprob", 0.0), _num(s, "no_speech_prob", 0.0), _num(s, "compression_ratio", 1.0))
                for s in segments]
        keep, reasons, confidence = self.assess_fn(rows, prompt, sorted(phrases))
        kept = [r[0] for r, ok in zip(rows, keep) if ok]
        dropped = tuple((r[0], why) for r, ok, why in zip(rows, keep, reasons) if not ok)
        words = [w for s, ok in zip(segments, keep) if ok for w in _words(s)]
        if not words or len(words) > MAX_WORDS:
            text = " ".join(kept).strip()
            return Heard(text, confidence, (), dropped)
        text, fixes = self._lexicon().correct(words, self.context())
        return Heard(" ".join(text.split()), confidence, tuple(fixes), dropped, words)


def _text(segment) -> str:
    text = getattr(segment, "text", "")
    return text.strip() if isinstance(text, str) else ""


def _num(segment, name: str, default: float) -> float:
    value = getattr(segment, name, default)
    return float(value) if isinstance(value, (int, float)) and not isinstance(value, bool) else default


def _words(segment) -> list[tuple[str, float]]:
    words = getattr(segment, "words", None)
    if not isinstance(words, (list, tuple)):
        return []
    return [(w.word, _num(w, "probability", 0.0)) for w in words if isinstance(getattr(w, "word", None), str)]


def _py_hear(segments: list, phrases: set[str]) -> Heard:
    text = " ".join(_text(s) for s in segments).strip()
    if text.lower().strip(" .") in phrases:
        return Heard("", 0.0, (), ((text, "frase tipica di rumore"),))
    return Heard(text, 1.0)
