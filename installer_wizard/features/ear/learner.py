import json
import logging
import os
import re
import time
import unicodedata
from pathlib import Path

log = logging.getLogger("nuxiva.ear")

def current_name() -> str:
    raw = os.environ.get("NUXIVA_ASSISTANT_NAME", "").strip()
    if not raw:
        try:
            from config import read_env
            raw = read_env().get("NUXIVA_ASSISTANT_NAME", "").strip()
        except Exception:
            pass
    clean = re.sub(r"^(?:hey|hei|ehi|hi|ok|okay)\s+", "", raw or "nuxiva", flags=re.I).strip()
    return clean.lower() or "nuxiva"


def get_aliases() -> list[str]:
    name = current_name()
    raw = os.environ.get("NUXIVA_WAKE_PHONETIC_ALIASES", "").strip()
    if not raw:
        try:
            from config import read_env
            raw = read_env().get("NUXIVA_WAKE_PHONETIC_ALIASES", "").strip()
        except Exception:
            pass
    aliases = [a.strip().lower() for a in raw.split(",") if a.strip()] if raw else []
    if name not in aliases:
        aliases.insert(0, name)
    return aliases


def get_wake_re() -> re.Pattern:
    name = current_name()
    if name == "nuxiva":
        return re.compile(r"\b((?:hey|hei|hej|ehi|ehy|eh|ei|e|hi|ok|okay)[\s,]+)?(nuxiva|nuxiba|nucsiva|nuxif|nuchiva)\b[\s,.!?:;-]*", re.I)
    aliases = get_aliases()
    pattern = "|".join(re.escape(a) for a in aliases)
    return re.compile(rf"\b((?:hey|hei|hej|ehi|ehy|eh|ei|e|hi|ok|okay)[\s,]+)?({pattern})\b[\s,.!?:;-]*", re.I)


NOT_NAMES = frozenset({"catena", "arena", "avena", "antenna", "atenei", "ateneo"})
LEARN_FILE = Path(os.environ.get("NUXIVA_EAR_LEARN", "/var/lib/nuxiva/ear_learning.json"))
PEOPLE_DIR = Path(os.environ.get("NUXIVA_PEOPLE_DIR", "/var/lib/nuxiva/people"))
TOKEN_RE = re.compile(r"[a-zàèéìòù']+", re.I)


def _plain(word: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", word.lower()) if unicodedata.category(c) != "Mn")


def _lev(a: str, b: str) -> int:
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


GREETINGS = frozenset({"hey", "hei", "hej", "ehi", "ehy", "eh", "ei", "e", "hi", "ok", "okay", "dis", "salut"})


def name_variant(text: str) -> str | None:
    tokens = [w for w in (_plain(t) for t in TOKEN_RE.findall(text or "")) if w not in GREETINGS][:3]
    candidates = tokens + [a + b for a, b in zip(tokens, tokens[1:]) if len(a) <= 3]
    name = current_name()
    if name == "nuxiva":
        scored = sorted((min(_lev(c, name), _lev(c, "nuxiva")), c) for c in candidates
                        if 3 <= len(c) <= 10 and not any(blocked in c for blocked in NOT_NAMES))
    else:
        aliases = get_aliases()
        scored = sorted((min(_lev(c, a) for a in aliases), c) for c in candidates
                        if 3 <= len(c) <= 10 and not any(blocked in c for blocked in NOT_NAMES))
    return scored[0][1] if scored and scored[0][0] <= 1 else None


class Learner:

    def __init__(self) -> None:
        self.data = {"variants": {}, "stats": {"wakes": 0, "fuzzy_wakes": 0, "commands": 0, "false_wakes": 0,
                                               "learned": 0, "wake_ms": []}, "strict": False}
        name = current_name()
        try:
            saved = json.loads(LEARN_FILE.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            saved = {}
        if isinstance(saved, dict) and saved.get("name") == name:
            self.data.update(saved)
        self.data["name"] = name
        self.recent_miss = None
        self.last_save = 0.0

    def save(self, force: bool = False) -> None:
        if not force and time.time() - self.last_save < 10:
            return
        self.last_save = time.time()
        try:
            LEARN_FILE.parent.mkdir(parents=True, exist_ok=True)
            LEARN_FILE.write_text(json.dumps(self.data, ensure_ascii=False, indent=1), encoding="utf-8")
        except OSError as exc:
            log.warning("Apprendimento non salvato: %s", exc)

    def hotwords(self) -> str:
        name = current_name().capitalize()
        names = set()
        try:
            for f in list(PEOPLE_DIR.glob("*.json"))[:50]:
                first = json.loads(f.read_text(encoding="utf-8")).get("first_name")
                if first and not first.lower().startswith("ospite") and first.lower() != name.lower():
                    names.add(first)
        except (OSError, ValueError):
            pass
        return " ".join([name] + sorted(names))

    def find_wake(self, text: str):
        exact = get_wake_re().search(text)
        if exact:
            return exact.start(), exact.end(), None
        tokens = list(TOKEN_RE.finditer(text))
        window = tokens[:2] if self.data.get("strict") else tokens[:4]
        for i, m in enumerate(window):
            candidates = [(_plain(m.group()), m)]
            if i + 1 < len(window) and len(m.group()) <= 3:
                candidates.append((_plain(m.group()) + _plain(window[i + 1].group()), window[i + 1]))
            for word, last in candidates:
                if self._sounds_like_name(word):
                    return m.start(), self._skip_punctuation(text, last.end()), word
        return None

    def _sounds_like_name(self, word: str) -> bool:
        if len(word) < 3 or len(word) > 10 or word in NOT_NAMES:
            return False
        learned = self.data["variants"].get(word, 0)
        name = current_name()
        if name == "nuxiva":
            dist = min(_lev(word, name), _lev(word, "nuxiva"))
        else:
            aliases = get_aliases()
            dist = min(_lev(word, a) for a in aliases)
        return dist <= 1 or learned >= 2 or (dist == 2 and learned >= 1)

    @staticmethod
    def _skip_punctuation(text: str, end: int) -> int:
        while end < len(text) and text[end] in " ,.!?:;-":
            end += 1
        return end

    def on_wake(self, variant, ms: int) -> None:
        s = self.data["stats"]
        s["wakes"] += 1
        s["wake_ms"] = (s.get("wake_ms", []) + [ms])[-50:]
        if variant:
            s["fuzzy_wakes"] += 1
            self.data["variants"][variant] = self.data["variants"].get(variant, 0) + 1
        self.save()

    def on_command(self) -> None:
        self.data["stats"]["commands"] += 1
        self.save()

    def on_false_wake(self) -> None:
        s = self.data["stats"]
        s["false_wakes"] += 1
        total = max(1, s["wakes"])
        self.data["strict"] = total >= 10 and s["false_wakes"] / total > 0.3
        self.save()

    def on_miss(self, text: str) -> None:
        tokens = TOKEN_RE.findall(text)
        if tokens:
            self.recent_miss = (time.time(), _plain(tokens[0]))

    def on_manual_listen(self) -> None:
        if self.recent_miss and time.time() - self.recent_miss[0] < 8:
            word = self.recent_miss[1]
            name = current_name()
            dist = min(_lev(word, name), _lev(word, "nuxiva")) if name == "nuxiva" else min(_lev(word, a) for a in get_aliases())
            if 3 <= len(word) <= 10 and word not in NOT_NAMES and dist <= 3:
                self.data["variants"][word] = self.data["variants"].get(word, 0) + 1
                self.data["stats"]["learned"] += 1
                log.info("Imparata la variante «%s»", word)
                self.save(force=True)
        self.recent_miss = None

    def learn_variant(self, word: str) -> bool:
        word = _plain(word)
        name = current_name()
        dist = min(_lev(word, name), _lev(word, "nuxiva")) if name == "nuxiva" else min(_lev(word, a) for a in get_aliases())
        if not 3 <= len(word) <= 10 or word in NOT_NAMES or dist > 3:
            return False
        self.data["variants"][word] = self.data["variants"].get(word, 0) + 1
        self.data["stats"]["learned"] += 1
        self.save()
        return True

    def teach(self, word: str) -> bool:
        word = _plain(word)
        name = current_name()
        dist = min(_lev(word, name), _lev(word, "nuxiva")) if name == "nuxiva" else min(_lev(word, a) for a in get_aliases())
        if not 3 <= len(word) <= 10 or word in NOT_NAMES or dist > 3:
            return False
        self.data["variants"][word] = max(2, self.data["variants"].get(word, 0) + 1)
        self.data["stats"]["learned"] += 1
        self.save(force=True)
        log.info("Variante «%s» insegnata durante l'addestramento vocale", word)
        return True

    def on_review(self, missed: int, false_instant: int) -> None:
        s = self.data["stats"]
        s["review_missed"] = s.get("review_missed", 0) + missed
        s["review_false_instant"] = s.get("review_false_instant", 0) + false_instant
        self.save()

    def summary(self) -> dict:
        s = self.data["stats"]
        ms = s.get("wake_ms") or [0]
        return {"wakes": s["wakes"], "commands": s["commands"], "false_wakes": s["false_wakes"],
                "fuzzy_wakes": s["fuzzy_wakes"], "avg_wake_ms": int(sum(ms) / len(ms)),
                "variants": {k: v for k, v in sorted(self.data["variants"].items(), key=lambda x: -x[1])[:15]},
                "strict": self.data.get("strict", False)}


learner = Learner()
