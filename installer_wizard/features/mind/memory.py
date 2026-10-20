import logging
import threading
import time
import uuid
from copy import deepcopy

from config import ETC_DIR, STATE_DIR

from features.mind import scoring
from features.mind import text as T
from features.mind.persistence import MemoryStorageError, PrivateDocument
from features.mind.records import MemoryInputError, active, content, limbic_state, metadata, number, validate_facts

MIND_DIR = STATE_DIR / "mind"
FACTS_FILE = MIND_DIR / "facts.json"
MEMORY_KEY = ETC_DIR / "mind.key"
MAX_FACTS = 400
log = logging.getLogger("nuxiva.mind.memory")


class LongTermMemory:
    def __init__(self) -> None:
        self.lock = threading.RLock()
        self.storage = PrivateDocument(FACTS_FILE, MEMORY_KEY, validate_facts)
        self.storage_error = ""
        self.facts: list = []
        try:
            self.facts = self.storage.load([])
        except MemoryStorageError as exc:
            self.storage_error = str(exc)
            log.error("Memoria non disponibile: %s", self.storage_error)

    def _ready(self) -> None:
        if self.storage_error:
            raise MemoryStorageError(self.storage_error)

    def _commit(self, facts: list) -> None:
        self._ready()
        try:
            self.storage.save(facts)
        except MemoryStorageError as exc:
            self.storage_error = str(exc)
            log.error("Memoria non salvata: %s", self.storage_error)
            raise
        self.facts = facts

    def save(self) -> None:
        with self.lock:
            self._commit(deepcopy(self.facts))

    def add(self, text: str, kind: str = "fatto", score: float = 0.6, who: str = "", limbic: dict | None = None,
            *, origin: str = "conversation", scope: str | None = None, expires_at=None) -> dict:
        text = content(text)
        meta = metadata(who, scope, origin, expires_at)
        score = number(score, 0, 1)
        limbic_data = limbic_state(limbic)
        if not isinstance(kind, str) or not 1 <= len(kind) <= 30:
            raise MemoryInputError("invalid_memory")
        with self.lock:
            self._ready()
            facts = deepcopy(self.facts)
            for fact in facts:
                if fact["who"] == who and fact["scope"] == meta["scope"] and active(fact) and T.plain(fact["text"]) == T.plain(text):
                    return deepcopy(fact)
            if len(facts) >= MAX_FACTS:
                raise MemoryInputError("memory_full")
            now = time.time()
            fact = {"id": uuid.uuid4().hex[:8], "text": text, "kind": kind, "score": round(score, 2),
                    **meta, "created": now, "updated": now, "hits": 0, "rehearsals": 1, "revision": 1,
                    "history": [], "limbic": limbic_data}
            facts.append(fact)
            self._commit(facts)
            return deepcopy(fact)

    def recall(self, query: str, k: int = 4, who: str = "") -> list:
        metadata(who, None, "conversation", None)
        with self.lock:
            self._ready()
            facts = deepcopy(self.facts)
            scored = []
            for fact in facts:
                visible = fact["scope"] == "shared" or fact["scope"] == "personal" and who and fact["who"] == who
                if not visible or not active(fact):
                    continue
                rel = T.overlap(query, fact["text"])
                if rel >= 0.34:
                    scored.append((scoring.score_memory_retention(fact, rel), fact))
            scored.sort(key=lambda pair: -pair[0])
            hits = [fact for _, fact in scored[:max(0, min(int(k), 20))]]
            for fact in hits:
                fact["hits"] = fact.get("hits", 0) + 1
                fact["rehearsals"] = fact.get("rehearsals", 1) + 1
            if hits:
                self._commit(facts)
            return deepcopy(hits)

    def update(self, fid: str, changes: dict, *, who: str | None = None) -> dict | None:
        if not isinstance(changes, dict) or not changes or set(changes) - {"text", "scope", "expires_at", "revision"}:
            raise MemoryInputError("invalid_memory")
        with self.lock:
            self._ready()
            facts = deepcopy(self.facts)
            fact = next((f for f in facts if f["id"] == fid and (who is None or f["who"] == who)), None)
            if fact is None:
                return None
            revision = changes.get("revision", fact["revision"])
            if isinstance(revision, bool) or not isinstance(revision, int) or revision != fact["revision"]:
                raise MemoryInputError("memory_conflict")
            corrected = content(changes.get("text", fact["text"]))
            meta = metadata(fact["who"], changes.get("scope", fact["scope"]), "manual",
                            changes.get("expires_at", fact["expires_at"]))
            fact["history"] = (fact.get("history", []) + [{key: deepcopy(fact.get(key)) for key in
                                ("text", "scope", "origin", "expires_at", "updated", "revision")}])[-5:]
            fact.update(text=corrected, **meta, updated=time.time(), revision=fact["revision"] + 1)
            self._commit(facts)
            return deepcopy(fact)

    def forget(self, fid: str, *, who: str | None = None) -> bool:
        with self.lock:
            self._ready()
            facts = [deepcopy(f) for f in self.facts if not (f["id"] == fid and (who is None or f["who"] == who))]
            if len(facts) == len(self.facts):
                return False
            self._commit(facts)
            return True

    def clear(self) -> int:
        with self.lock:
            count = len(self.facts)
            self._commit([])
            return count

    def listing(self, *, who: str | None = None) -> list:
        with self.lock:
            self._ready()
            return deepcopy(sorted((f for f in self.facts if who is None or f["who"] == who), key=lambda f: -f["updated"]))

    def stats(self) -> dict:
        with self.lock:
            kinds: dict = {}
            for fact in self.facts:
                kinds[fact["kind"]] = kinds.get(fact["kind"], 0) + 1
            return {"count": len(self.facts), "kinds": kinds, "encrypted": not bool(self.storage_error),
                    "storage_error": self.storage_error, "expired": sum(not active(f) for f in self.facts)}
