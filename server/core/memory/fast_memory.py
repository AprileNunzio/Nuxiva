import json
import math
import time
from typing import Any, Dict, List, Optional


class MemoryHit:
    def __init__(
        self,
        key: str,
        response_key: str,
        payload_json: str,
        similarity: float,
        hit_count: int,
    ) -> None:
        self.key = key
        self.response_key = response_key
        self.payload_json = payload_json
        self.similarity = float(similarity)
        self.hit_count = int(hit_count)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "key": self.key,
            "response_key": self.response_key,
            "payload_json": self.payload_json,
            "similarity": self.similarity,
            "hit_count": self.hit_count,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MemoryHit":
        return cls(
            key=str(data.get("key", "")),
            response_key=str(data.get("response_key", "")),
            payload_json=str(data.get("payload_json", "{}")),
            similarity=float(data.get("similarity", 0.0)),
            hit_count=int(data.get("hit_count", 0)),
        )


class FastMemoryBridge:
    def __init__(self, max_capacity: int = 512) -> None:
        self.max_capacity = max_capacity
        self._native = None
        self._py_entries: List[Dict[str, Any]] = []

        try:
            import nuxiva_native
            if hasattr(nuxiva_native, "RustFastMemory"):
                self._native = nuxiva_native.RustFastMemory(max_capacity)
        except ImportError:
            self._native = None

    def insert(
        self,
        key: str,
        embedding: List[float],
        response_key: str,
        payload: Optional[Dict[str, Any]] = None,
        timestamp_ms: Optional[int] = None,
    ) -> None:
        ts = int(time.time() * 1000) if timestamp_ms is None else int(timestamp_ms)
        p_json = json.dumps(payload or {})

        if self._native is not None:
            self._native.insert(key, embedding, response_key, p_json, ts)
            return

        for e in self._py_entries:
            if e["key"] == key:
                e["embedding"] = embedding
                e["response_key"] = response_key
                e["payload_json"] = p_json
                e["timestamp_ms"] = ts
                return

        if len(self._py_entries) >= self.max_capacity:
            self.prune_lru(max(0, self.max_capacity - 1))

        self._py_entries.append({
            "key": key,
            "embedding": embedding,
            "response_key": response_key,
            "payload_json": p_json,
            "hit_count": 0,
            "timestamp_ms": ts,
        })

    def lookup(
        self,
        exact_key: str,
        query_embedding: Optional[List[float]] = None,
        similarity_threshold: float = 0.82,
    ) -> Optional[MemoryHit]:
        q_emb = query_embedding or []

        if self._native is not None:
            raw = self._native.lookup_json(exact_key, q_emb, float(similarity_threshold))
            if raw is None:
                return None
            return MemoryHit.from_dict(json.loads(raw))

        for e in self._py_entries:
            if e["key"] == exact_key:
                e["hit_count"] += 1
                return MemoryHit(
                    key=e["key"],
                    response_key=e["response_key"],
                    payload_json=e["payload_json"],
                    similarity=1.0,
                    hit_count=e["hit_count"],
                )

        if not q_emb:
            return None

        best_entry = None
        best_sim = similarity_threshold

        for e in self._py_entries:
            sim = self._compute_cosine_similarity(e["embedding"], q_emb)
            if sim > best_sim:
                best_sim = sim
                best_entry = e

        if best_entry is not None:
            best_entry["hit_count"] += 1
            return MemoryHit(
                key=best_entry["key"],
                response_key=best_entry["response_key"],
                payload_json=best_entry["payload_json"],
                similarity=best_sim,
                hit_count=best_entry["hit_count"],
            )

        return None

    def prune_lru(self, target_size: int) -> None:
        if self._native is not None:
            self._native.prune_lru(target_size)
            return

        if len(self._py_entries) <= target_size:
            return

        self._py_entries.sort(key=lambda x: (x["hit_count"], x["timestamp_ms"]), reverse=True)
        self._py_entries = self._py_entries[:target_size]

    def clear(self) -> None:
        if self._native is not None:
            self._native.clear()
        else:
            self._py_entries.clear()

    def __len__(self) -> int:
        if self._native is not None:
            return int(self._native.len())
        return len(self._py_entries)

    @staticmethod
    def _compute_cosine_similarity(vec_a: List[float], vec_b: List[float]) -> float:
        if not vec_a or len(vec_a) != len(vec_b):
            return 0.0

        dot = sum(a * b for a, b in zip(vec_a, vec_b))
        norm_a = math.sqrt(sum(a * a for a in vec_a))
        norm_b = math.sqrt(sum(b * b for b in vec_b))

        denom = norm_a * norm_b
        if denom < 1e-7:
            return 0.0

        val = dot / denom
        return max(-1.0, min(1.0, val))
