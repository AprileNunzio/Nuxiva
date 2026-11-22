"""Knowledge base per progetto (RAG locale).

Indicizza documenti di testo in chunk su SQLite FTS5 (ranking BM25): nessuna
dipendenza esterna e nessun dato che esce dalla macchina. Il recupero restituisce
snippet con la fonte, da iniettare nel prompt come contesto citabile.
"""

import re
import time
import uuid
from typing import Any, Dict, List

from .store import StudioStore

CHUNK_CHARS = 900
CHUNK_OVERLAP = 120
MAX_DOC_CHARS = 400_000
_TOKEN_RE = re.compile(r"\w{2,}", re.UNICODE)


def chunk_text(text: str, size: int = CHUNK_CHARS, overlap: int = CHUNK_OVERLAP) -> List[str]:
    text = text.replace("\r\n", "\n").strip()
    if not text:
        return []
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    chunks: List[str] = []
    current = ""
    for para in paragraphs:
        if len(para) > size:
            if current:
                chunks.append(current)
                current = ""
            step = max(1, size - overlap)
            for start in range(0, len(para), step):
                chunks.append(para[start:start + size])
            continue
        if current and len(current) + len(para) + 2 > size:
            chunks.append(current)
            current = para
        else:
            current = f"{current}\n\n{para}" if current else para
    if current:
        chunks.append(current)
    return chunks


def build_match_query(query: str) -> str:
    tokens = _TOKEN_RE.findall(query.lower())[:12]
    return " OR ".join(f'"{t}"' for t in tokens)


class KnowledgeService:
    def __init__(self, store: StudioStore) -> None:
        self.store = store
        self._init_schema()

    def _init_schema(self) -> None:
        with self.store._lock, self.store._get_connection() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS knowledge_docs (
                    id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    chars INTEGER NOT NULL,
                    chunks INTEGER NOT NULL,
                    created_at INTEGER NOT NULL
                );
                CREATE VIRTUAL TABLE IF NOT EXISTS knowledge_fts USING fts5(
                    content, doc_id UNINDEXED, project_id UNINDEXED, name UNINDEXED,
                    tokenize = 'unicode61 remove_diacritics 2'
                );
                """
            )

    def add_document(self, project_id: str, name: str, text: str) -> Dict[str, Any]:
        text = text[:MAX_DOC_CHARS]
        chunks = chunk_text(text)
        doc_id = f"doc_{int(time.time())}_{uuid.uuid4().hex[:6]}"
        now = int(time.time())
        with self.store._lock, self.store._get_connection() as conn:
            conn.execute(
                "INSERT INTO knowledge_docs (id, project_id, name, chars, chunks, created_at) VALUES (?,?,?,?,?,?)",
                (doc_id, project_id, name, len(text), len(chunks), now),
            )
            conn.executemany(
                "INSERT INTO knowledge_fts (content, doc_id, project_id, name) VALUES (?,?,?,?)",
                [(c, doc_id, project_id, name) for c in chunks],
            )
        return {"id": doc_id, "project_id": project_id, "name": name, "chars": len(text), "chunks": len(chunks), "created_at": now}

    def list_documents(self, project_id: str) -> List[Dict[str, Any]]:
        with self.store._lock, self.store._get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM knowledge_docs WHERE project_id = ? ORDER BY created_at DESC", (project_id,)
            ).fetchall()
        return [dict(r) for r in rows]

    def delete_document(self, project_id: str, doc_id: str) -> bool:
        with self.store._lock, self.store._get_connection() as conn:
            cur = conn.execute(
                "DELETE FROM knowledge_docs WHERE id = ? AND project_id = ?", (doc_id, project_id)
            )
            if cur.rowcount:
                conn.execute("DELETE FROM knowledge_fts WHERE doc_id = ?", (doc_id,))
            return bool(cur.rowcount)

    def delete_project(self, project_id: str) -> None:
        with self.store._lock, self.store._get_connection() as conn:
            conn.execute("DELETE FROM knowledge_fts WHERE project_id = ?", (project_id,))
            conn.execute("DELETE FROM knowledge_docs WHERE project_id = ?", (project_id,))

    def search(self, project_id: str, query: str, limit: int = 4) -> List[Dict[str, Any]]:
        match = build_match_query(query)
        if not match:
            return []
        with self.store._lock, self.store._get_connection() as conn:
            rows = conn.execute(
                """
                SELECT doc_id, name, content, bm25(knowledge_fts) AS score
                FROM knowledge_fts
                WHERE knowledge_fts MATCH ? AND project_id = ?
                ORDER BY score LIMIT ?
                """,
                (match, project_id, limit),
            ).fetchall()
        return [
            {"doc_id": r["doc_id"], "source": r["name"], "snippet": r["content"], "score": r["score"]}
            for r in rows
        ]

    def build_context(self, project_id: str, query: str, limit: int = 3) -> str:
        hits = self.search(project_id, query, limit=limit)
        if not hits:
            return ""
        lines = ["[Conoscenza del progetto - cita la fonte tra parentesi quadre quando la usi]"]
        for i, h in enumerate(hits, 1):
            lines.append(f"({i}) [{h['source']}]: {h['snippet']}")
        return "\n".join(lines)
