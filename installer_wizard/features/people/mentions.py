import re
import threading
import time

from features.people import people

REFRESH_SECONDS = 60.0
MIN_TOKEN = 3
GENERIC = re.compile(r"^(ospite|sconosciut[oa]|guest|unknown)\b", re.I)


class Mentions:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._index: list[tuple[re.Pattern, str]] = []
        self._at = 0.0

    def _build(self) -> list[tuple[re.Pattern, str]]:
        names: dict[str, set[str]] = {}
        for p in people.all_profiles(light=True):
            slug, full = p.get("slug") or "", " ".join(str(p.get("name") or "").split())
            if not slug or not full or GENERIC.match(full):
                continue
            first = str(p.get("first_name") or full.split(" ")[0]).strip()
            nick = str(p.get("nickname") or "").strip()
            for token in {full, first, nick} - {""}:
                if len(token) >= MIN_TOKEN:
                    names.setdefault(token.lower(), set()).add(slug)
        index = []
        for token, slugs in sorted(names.items(), key=lambda kv: -len(kv[0])):
            if len(slugs) == 1:
                index.append((re.compile(r"(?<![\wÀ-ÿ])" + re.escape(token) + r"(?![\wÀ-ÿ])", re.I), next(iter(slugs))))
        return index

    def index(self, now: float | None = None) -> list[tuple[re.Pattern, str]]:
        now = now or time.time()
        with self._lock:
            if now - self._at > REFRESH_SECONDS:
                self._index, self._at = self._build(), now
            return self._index

    def invalidate(self) -> None:
        with self._lock:
            self._at = 0.0

    def find(self, text: str) -> list[str]:
        flat = " ".join(str(text or "").split())[:2000]
        found: list[str] = []
        for rx, slug in self.index():
            if slug not in found and rx.search(flat):
                found.append(slug)
        return found

    def owner(self, text: str, speaker: str = "") -> str:
        found = [s for s in self.find(text) if s != speaker]
        return found[0] if len(found) == 1 else ""


mentions = Mentions()
