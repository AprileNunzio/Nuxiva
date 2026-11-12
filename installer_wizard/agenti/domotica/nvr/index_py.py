import hashlib
import hmac
import json
import math

MAX_DOCS = 2_000_000
MAX_TOKENS = 512
MAX_QUERY_TOKENS = 12
MIN_TOKEN = 2
MIN_PREFIX = 4
MAX_PREFIX = 12
MAX_TEXT = 16_000
MAX_LIMIT = 20_000
FOLD = {**dict.fromkeys("àáâäãå", "a"), **dict.fromkeys("èéêë", "e"), **dict.fromkeys("ìíîï", "i"),
        **dict.fromkeys("òóôöõ", "o"), **dict.fromkeys("ùúûü", "u"), "ç": "c", "ñ": "n"}


def _fold(c: str) -> str:
    lower = c.lower()[:1] or c
    base = FOLD.get(lower, lower)
    return base if base.isascii() and base.isalnum() else " "


def tokens(text: str) -> list[str]:
    folded = "".join(_fold(c) for c in text)
    return [t for t in folded.split() if len(t) >= MIN_TOKEN][:MAX_TOKENS]


class PyNvrIndex:
    def __init__(self, key: bytes) -> None:
        if len(key) != 32:
            raise ValueError("nvr.index.key")
        self.key = bytes(key)
        self.docs: list = []
        self.by_key: dict[str, int] = {}
        self.postings: dict[str, list] = {}

    def _blind(self, label: str, token: str) -> str:
        return hmac.new(self.key, (label + token).encode(), hashlib.sha256).digest()[:16].hex()

    @staticmethod
    def from_json(key: bytes, text: str) -> "PyNvrIndex":
        data = json.loads(text)
        if len(data["docs"]) > MAX_DOCS:
            raise ValueError("nvr.catalog.too_many")
        out = PyNvrIndex(key)
        out.docs = data["docs"]
        out.postings = {k: [list(p) for p in v] for k, v in data["postings"].items()}
        out.by_key = {d["key"]: i for i, d in enumerate(out.docs) if d}
        return out

    def to_json(self) -> str:
        return json.dumps({"docs": self.docs, "postings": {k: self.postings[k] for k in sorted(self.postings)}},
                          separators=(",", ":"), ensure_ascii=False)

    def __len__(self) -> int:
        return len(self.by_key)

    def _grams(self, text: str) -> dict[str, int]:
        out: dict[str, int] = {}
        for token in tokens(text):
            exact = self._blind("t:", token)
            out[exact] = min(65535, out.get(exact, 0) + 1)
            for n in range(MIN_PREFIX, min(len(token), MAX_PREFIX + 1)):
                out.setdefault(self._blind("p:", token[:n]), 1)
        return out

    def add(self, meta_json: str, text: str) -> None:
        raw = json.loads(meta_json)
        meta = {"key": str(raw["key"]), "camera": str(raw["camera"]), "at_ms": int(raw["at_ms"]), "kind": str(raw["kind"])}
        if len(text.encode()) > MAX_TEXT or not meta["key"] or len(meta["key"].encode()) > 200:
            raise ValueError("nvr.segment.invalid")
        self.remove(meta["key"])
        if len(self.by_key) >= MAX_DOCS:
            raise ValueError("nvr.catalog.too_many")
        doc = len(self.docs)
        for gram, tf in sorted(self._grams(text).items()):
            self.postings.setdefault(gram, []).append([doc, tf])
        self.by_key[meta["key"]] = doc
        self.docs.append(meta)

    def _drop(self, ids: set[int]) -> None:
        for i in ids:
            self.docs[i] = None
        for gram in list(self.postings):
            kept = [p for p in self.postings[gram] if p[0] not in ids]
            if kept:
                self.postings[gram] = kept
            else:
                del self.postings[gram]

    def remove(self, key: str) -> bool:
        doc = self.by_key.pop(key, None)
        if doc is None:
            return False
        self._drop({doc})
        return True

    def remove_prefix(self, prefix: str) -> int:
        ids = {self.by_key.pop(k) for k in [k for k in self.by_key if k.startswith(prefix)]}
        if ids:
            self._drop(ids)
        return len(ids)

    def search(self, query: str, camera: str | None, from_ms: int, to_ms: int, limit: int) -> str:
        terms = tokens(query)[:MAX_QUERY_TOKENS]
        limit = min(limit, MAX_LIMIT)
        if not terms or limit <= 0:
            return "[]"
        total = float(max(1, len(self.by_key)))
        scores: dict[int, list] = {}
        for term in terms:
            matched: dict[int, int] = {}
            for label in (("t:", "p:") if len(term) >= MIN_PREFIX else ("t:",)):
                for doc, tf in self.postings.get(self._blind(label, term), []):
                    matched[doc] = max(matched.get(doc, 0), tf)
            idf = math.log(1.0 + total / max(1, len(matched)))
            for doc, tf in matched.items():
                entry = scores.setdefault(doc, [0.0, 0])
                entry[0] += idf * (1.0 + math.log(tf))
                entry[1] += 1
        hits = []
        for doc, (score, n) in scores.items():
            meta = self.docs[doc] if doc < len(self.docs) else None
            if n != len(terms) or not meta or not from_ms <= meta["at_ms"] < to_ms or (camera is not None and meta["camera"] != camera):
                continue
            hits.append({**meta, "score": math.floor(score * 1e6 + 0.5) / 1e6})
        hits.sort(key=lambda h: (-h["score"], -h["at_ms"], h["key"]))
        return json.dumps(hits[:limit])
