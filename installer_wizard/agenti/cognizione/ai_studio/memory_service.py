import json
import re
import time
import uuid
from typing import List
from .models import MemoryFact
from .store import StudioStore

try:
    import nuxiva_native
except ImportError:
    nuxiva_native = None

TOKEN_SPLIT_RE = re.compile(r"[\s\.,;:!?\-_'\"()\[\]{}]+", re.UNICODE)


class CrossMemoryService:
    def __init__(self, store: StudioStore) -> None:
        self.store = store
        self._rust_studio = None
        if nuxiva_native and hasattr(nuxiva_native, "RustChatStudio"):
            try:
                self._rust_studio = nuxiva_native.RustChatStudio()
            except Exception:
                self._rust_studio = None

    def _get_voice_facts(self, limit: int = 50) -> List[MemoryFact]:
        facts: List[MemoryFact] = []
        try:
            from agenti.ear.journal import Journal
            journal = Journal()
            entries = journal.entries(limit=limit)
            for entry in entries:
                text = (entry.get("text") or "").strip()
                if not text:
                    continue
                facts.append(
                    MemoryFact(
                        id=f"voice_{entry['id']}",
                        source="voice_speech",
                        content=text,
                        speaker=entry.get("speaker") or "user",
                        timestamp=int(entry.get("ts") or time.time()),
                        tags=["voice", "speech"],
                    )
                )
        except Exception:
            pass
        return facts

    def get_all_facts(self) -> List[MemoryFact]:
        stored_facts = self.store.get_all_memory()
        voice_facts = self._get_voice_facts(limit=40)
        combined = stored_facts + voice_facts
        combined.sort(key=lambda f: f.timestamp, reverse=True)
        return combined

    def learn(self, content: str, source: str = "written_chat", speaker: str = "", tags: List[str] | None = None) -> MemoryFact:
        now_ts = int(time.time())
        fact = MemoryFact(
            id=f"fact_{now_ts}_{uuid.uuid4().hex[:8]}",
            source=source,
            content=content.strip(),
            speaker=speaker,
            timestamp=now_ts,
            tags=tags or [],
        )
        self.store.add_memory(fact)
        if self._rust_studio:
            try:
                self._rust_studio.learn_statement(
                    fact.content,
                    "voice" if "voice" in source else "written",
                    now_ts * 1000,
                )
            except Exception:
                pass
        return fact

    def consolidate_and_prune(self, max_facts: int = 1000, half_life_seconds: int = 86400) -> dict:
        consolidated = 0
        pruned = 0
        if self._rust_studio:
            try:
                consolidated = int(self._rust_studio.memory_consolidate())
                now_ms = int(time.time() * 1000)
                half_life_ms = half_life_seconds * 1000
                pruned = int(self._rust_studio.memory_prune(now_ms, max_facts, half_life_ms))
            except Exception:
                pass
        return {"consolidated": consolidated, "pruned": pruned}

    def recall(self, query: str, limit: int = 5) -> List[MemoryFact]:
        all_facts = self.get_all_facts()
        if not query.strip() or not all_facts:
            return all_facts[:limit]

        if self._rust_studio:
            try:
                raw_json = self._rust_studio.recall_memory_json(query, limit)
                recalled = json.loads(raw_json)
                return [
                    MemoryFact(
                        id=f"recall_{i}",
                        source=item.get("source", "written"),
                        content=item.get("content", ""),
                        speaker=item.get("speaker", ""),
                        timestamp=item.get("timestamp", int(time.time())),
                        tags=[],
                    )
                    for i, item in enumerate(recalled)
                ]
            except Exception:
                pass

        query_tokens = {t.lower() for t in TOKEN_SPLIT_RE.split(query) if len(t) >= 3}
        scored = []
        for fact in all_facts:
            fact_tokens = {t.lower() for t in TOKEN_SPLIT_RE.split(fact.content) if len(t) >= 3}
            score = len(query_tokens.intersection(fact_tokens))
            if score > 0:
                scored.append((score, fact))

        scored.sort(key=lambda pair: (pair[0], pair[1].timestamp), reverse=True)
        return [pair[1] for pair in scored[:limit]]

    def build_system_injection(self, query: str) -> str:
        if self._rust_studio:
            try:
                res = self._rust_studio.build_system_injection(query)
                if res.strip():
                    return res
            except Exception:
                pass

        recalls = self.recall(query, limit=5)
        if not recalls:
            return ""

        lines = ["[Nuxiva Cross-Thread & Voice Memory Context]"]
        for fact in recalls:
            prefix = "[Voice Speech]" if "voice" in fact.source else "[Written Chat]"
            spk = f" ({fact.speaker})" if fact.speaker else ""
            lines.append(f"- {prefix}{spk}: {fact.content}")
        lines.append("[End of Memory Context]\n")
        return "\n".join(lines)
