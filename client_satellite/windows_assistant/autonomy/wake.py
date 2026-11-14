import difflib
import re
import time
import unicodedata

THRESHOLD = 0.78
LOOKAHEAD = 4
FOLLOWUP_DEFAULT = 8.0
FILLERS = {"hey", "hei", "ehi", "ok", "okay", "ciao", "salut", "hola", "hi"}


def fold(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text)
    stripped = "".join(c for c in decomposed if not unicodedata.combining(c))
    return re.sub(r"[^\w\s']", " ", stripped.casefold())


def words(text: str) -> list[str]:
    return fold(text).split()


class WakeGate:
    def __init__(self, names) -> None:
        self.names = names
        self.followup_until = 0.0

    def open_followup(self, seconds: float = FOLLOWUP_DEFAULT, now: float | None = None) -> None:
        self.followup_until = (time.monotonic() if now is None else now) + max(0.0, seconds)

    def _targets(self) -> list[str]:
        return [fold(n).strip() for n in self.names() if isinstance(n, str) and fold(n).strip()]

    def _match(self, tokens: list[str]) -> int:
        for target in self._targets():
            size = len(target.split())
            for start in range(0, min(LOOKAHEAD, len(tokens)) - size + 1):
                phrase = " ".join(tokens[start:start + size])
                if difflib.SequenceMatcher(None, phrase, target).ratio() >= THRESHOLD:
                    return start + size
        return 0

    def process(self, text: str, now: float | None = None) -> tuple[str, str] | None:
        moment = time.monotonic() if now is None else now
        tokens = words(text)
        if not tokens:
            return None
        end = self._match(tokens)
        if end:
            rest = " ".join(t for t in tokens[end:])
            return rest, "wake"
        if moment < self.followup_until:
            return " ".join(tokens), "followup"
        return None

    def command_text(self, original: str, remainder: str) -> str:
        if not remainder:
            return ""
        parts = original.split()
        keep = len(remainder.split())
        return " ".join(parts[-keep:]).strip(" ,.:;!?-") if keep <= len(parts) else remainder
