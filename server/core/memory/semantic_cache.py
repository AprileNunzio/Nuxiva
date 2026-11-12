import logging
import math
import os
import re
import threading
import time
import uuid
from collections import OrderedDict
from typing import Any, Callable, Dict, List, Literal, Optional

from pydantic import BaseModel, ValidationError

from server.config.env import settings
from server.core.memory.cache_policy import CacheScope, MAX_TTL_SECONDS, PureResultPolicy, canonical, digest, safe_payload, unit_vector
from server.core.memory.cache_storage import EncryptedCacheStorage

logger = logging.getLogger("nuxiva.semantic_cache")


class CacheEntry(BaseModel):
    id: str
    key_digest: str
    scope_digest: str
    policy_id: str
    query: str
    embedding: List[float]
    action_result: Dict[str, Any]
    created_at: float
    expires_at: float
    validation_state: Literal["verified"]
    hit_count: int = 0
    last_hit: float = 0.0


class CacheLookupResult(BaseModel):
    hit: bool
    similarity: float = 0.0
    action_result: Optional[Dict[str, Any]] = None
    cached_query: Optional[str] = None
    lookup_latency_ms: float = 0.0
    strategy: str = "miss"
    validation_state: str = "miss"


class SemanticCache:
    def __init__(self, storage_path: Optional[str] = None, similarity_threshold: Optional[float] = None,
                 max_entries: int = 128, max_storage_bytes: int = 1_048_576,
                 clock: Callable[[], float] = time.time) -> None:
        self.storage_path = storage_path or os.path.join(settings.DATA_DIR, "semantic_cache.json")
        self.similarity_threshold = settings.SEMANTIC_CACHE_THRESHOLD if similarity_threshold is None else similarity_threshold
        if not math.isfinite(self.similarity_threshold) or not 0 <= self.similarity_threshold <= 1:
            raise ValueError("Invalid cache similarity threshold")
        if not 1 <= max_entries <= 4096 or not 4096 <= max_storage_bytes <= 16_777_216:
            raise ValueError("Invalid cache size limits")
        self.max_entries = max_entries
        self.max_storage_bytes = max_storage_bytes
        self._clock = clock
        self._entries: OrderedDict[str, CacheEntry] = OrderedDict()
        self._lock = threading.RLock()
        self._total_hits = 0
        self._total_lookups = 0
        self._storage = EncryptedCacheStorage(self.storage_path, lambda: settings.NUXIVA_SECRET_KEY, max_storage_bytes)
        if settings.SEMANTIC_CACHE_ENABLED:
            self._load_from_disk()

    @staticmethod
    def _normalize(text: str) -> str:
        return text.strip()

    @staticmethod
    def _cosine_similarity(v1: List[float], v2: List[float]) -> float:
        left, right = unit_vector(v1), unit_vector(v2)
        if left is None or right is None or len(left) != len(right):
            return 0.0
        return max(-1.0, min(1.0, sum(a * b for a, b in zip(left, right))))

    def _request_keys(self, query: str, scope: CacheScope, policy: PureResultPolicy) -> tuple[str, str] | None:
        if not isinstance(scope, CacheScope) or not isinstance(policy, PureResultPolicy) or not isinstance(query, str):
            return None
        if not query.strip() or len(query.encode("utf-8")) > 4096:
            return None
        try:
            scope_digest = scope.fingerprint(settings.NUXIVA_SECRET_KEY)
            key_digest = digest({"scope": scope_digest, "policy": policy.policy_id, "query": self._normalize(query)},
                                settings.NUXIVA_SECRET_KEY)
            return key_digest, scope_digest
        except (ValueError, TypeError, OverflowError, RecursionError) as exc:
            logger.warning("Cache scope cannot be canonicalized (%s)", type(exc).__name__)
            return None

    def _valid_entry(self, entry: CacheEntry, now: float) -> bool:
        return (bool(re.fullmatch(r"[a-f0-9]{64}", entry.key_digest))
                and bool(re.fullmatch(r"[a-f0-9]{64}", entry.scope_digest))
                and bool(entry.query.strip()) and len(entry.query.encode("utf-8")) <= 4096
                and math.isfinite(entry.created_at) and math.isfinite(entry.expires_at)
                and entry.created_at <= now < entry.expires_at
                and 0 < entry.expires_at - entry.created_at <= MAX_TTL_SECONDS
                and safe_payload(entry.action_result)
                and (not entry.embedding or unit_vector(entry.embedding) is not None))

    def _prune(self) -> bool:
        expired = [key for key, entry in self._entries.items() if not self._valid_entry(entry, self._clock())]
        for key in expired:
            del self._entries[key]
        while len(self._entries) > self.max_entries:
            self._entries.popitem(last=False)
        while self._entries and len(canonical(self._serialized())) > self.max_storage_bytes // 2:
            self._entries.popitem(last=False)
        return bool(expired)

    def _serialized(self) -> list:
        return [entry.model_dump() for entry in self._entries.values()]

    def _load_from_disk(self) -> None:
        for item in self._storage.load():
            try:
                entry = CacheEntry.model_validate(item)
                if self._valid_entry(entry, self._clock()):
                    self._entries[entry.key_digest] = entry
            except (ValidationError, TypeError, ValueError) as exc:
                logger.warning("Ignoring cache entry without a valid scope, TTL or payload (%s)", type(exc).__name__)
        self._prune()

    def _miss(self, started: float, strategy: str = "miss") -> CacheLookupResult:
        return CacheLookupResult(hit=False, lookup_latency_ms=(time.perf_counter() - started) * 1000, strategy=strategy)

    def lookup_sync(self, query: str, query_embedding: Optional[List[float]] = None, *,
                    scope: Optional[CacheScope] = None, policy: Optional[PureResultPolicy] = None) -> CacheLookupResult:
        started = time.perf_counter()
        with self._lock:
            self._total_lookups += 1
            if not settings.SEMANTIC_CACHE_ENABLED:
                return self._miss(started, "disabled")
            keys = self._request_keys(query, scope, policy)
            vector = unit_vector(query_embedding) if query_embedding is not None else None
            if keys is None or (query_embedding is not None and vector is None):
                return self._miss(started)
            key, scope_digest = keys
            if self._prune():
                self._storage.save(self._serialized())
            candidates = []
            if key in self._entries:
                candidates.append((1.0, "exact", self._entries[key]))
            if vector is not None and policy.allow_semantic:
                for entry in self._entries.values():
                    if entry.key_digest == key or entry.scope_digest != scope_digest or entry.policy_id != policy.policy_id:
                        continue
                    similarity = self._cosine_similarity(vector, entry.embedding)
                    if len(vector) == len(entry.embedding) and similarity >= self.similarity_threshold:
                        candidates.append((similarity, "semantic", entry))
            for similarity, strategy, entry in sorted(candidates, key=lambda item: item[0], reverse=True):
                if self._clock() >= min(entry.expires_at, entry.created_at + policy.ttl_seconds):
                    continue
                if not policy.accepts(query, entry.action_result, scope.context):
                    continue
                entry.hit_count += 1
                entry.last_hit = self._clock()
                self._entries.move_to_end(entry.key_digest)
                self._total_hits += 1
                return CacheLookupResult(hit=True, similarity=similarity, action_result=entry.model_copy(deep=True).action_result,
                                         cached_query=entry.query, lookup_latency_ms=(time.perf_counter() - started) * 1000,
                                         strategy=strategy, validation_state="verified")
            return self._miss(started)

    async def lookup(self, query: str, query_embedding: Optional[List[float]] = None, *,
                     scope: Optional[CacheScope] = None, policy: Optional[PureResultPolicy] = None) -> CacheLookupResult:
        return self.lookup_sync(query, query_embedding, scope=scope, policy=policy)

    async def record_success(self, query: str, action_result: Optional[Dict[str, Any]] = None,
                             embedding: Optional[List[float]] = None, *, scope: Optional[CacheScope] = None,
                             policy: Optional[PureResultPolicy] = None, result_data: Optional[Dict[str, Any]] = None) -> Optional[CacheEntry]:
        with self._lock:
            if not settings.SEMANTIC_CACHE_ENABLED:
                return None
            keys = self._request_keys(query, scope, policy)
            result = action_result if action_result is not None else result_data
            vector = unit_vector(embedding) if embedding is not None else []
            if keys is None or vector is None or not policy.accepts(query, result, scope.context):
                return None
            now = self._clock()
            entry = CacheEntry(id=uuid.uuid4().hex, key_digest=keys[0], scope_digest=keys[1], policy_id=policy.policy_id,
                               query=query, embedding=vector, action_result=result, created_at=now,
                               expires_at=now + policy.ttl_seconds, validation_state="verified")
            self._entries[entry.key_digest] = entry.model_copy(deep=True)
            self._entries.move_to_end(entry.key_digest)
            self._prune()
            if entry.key_digest not in self._entries:
                return None
            self._storage.save(self._serialized())
            return entry.model_copy(deep=True)

    def invalidate(self, *, scope: Optional[CacheScope] = None, policy_id: Optional[str] = None) -> int:
        with self._lock:
            scope_digest = scope.fingerprint(settings.NUXIVA_SECRET_KEY) if scope is not None else None
            keys = [key for key, entry in self._entries.items()
                    if (scope_digest is None or entry.scope_digest == scope_digest)
                    and (policy_id is None or entry.policy_id == policy_id)]
            for key in keys:
                del self._entries[key]
            if keys:
                self._storage.save(self._serialized())
            return len(keys)

    def clear(self) -> bool:
        with self._lock:
            self._entries.clear()
            self._total_hits = 0
            self._total_lookups = 0
            return self._storage.clear()

    def stats(self) -> Dict[str, Any]:
        with self._lock:
            if self._prune() and settings.SEMANTIC_CACHE_ENABLED:
                self._storage.save(self._serialized())
            return {"entries_count": len(self._entries), "total_lookups": self._total_lookups,
                    "total_hits": self._total_hits,
                    "hit_rate": round(self._total_hits / self._total_lookups, 4) if self._total_lookups else 0.0,
                    "threshold": self.similarity_threshold, "enabled": settings.SEMANTIC_CACHE_ENABLED}


semantic_cache = SemanticCache()
