import json
import time
from typing import Any, Dict, List, Optional

from .store import StudioStore

REACTIONS = ("❤️", "👍", "🚀", "💡", "🎯", "🔥", "👏", "🤔", "💬", "💯", "⚙️", "🛠️", "🧊", "✨")
FEEDBACK = ("positive", "negative")
AUTHOR_MAX = 64


class ReactionService:
    def __init__(self, store: StudioStore) -> None:
        self.store = store
        with self.store._lock, self.store._get_connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS message_marks (
                    message_id TEXT PRIMARY KEY,
                    reactions_json TEXT NOT NULL DEFAULT '{}',
                    feedback TEXT NOT NULL DEFAULT '',
                    updated_at INTEGER NOT NULL,
                    FOREIGN KEY(message_id) REFERENCES messages(id) ON DELETE CASCADE
                )
                """
            )

    def _owned(self, conn, thread_id: str, message_id: str) -> bool:
        row = conn.execute("SELECT 1 FROM messages WHERE id = ? AND thread_id = ?", (message_id, thread_id)).fetchone()
        return row is not None

    def _load(self, conn, message_id: str) -> Dict[str, Any]:
        row = conn.execute("SELECT reactions_json, feedback FROM message_marks WHERE message_id = ?", (message_id,)).fetchone()
        if not row:
            return {"reactions": {}, "feedback": ""}
        return {"reactions": json.loads(row["reactions_json"] or "{}"), "feedback": row["feedback"]}

    def _save(self, conn, message_id: str, marks: Dict[str, Any]) -> None:
        conn.execute(
            "INSERT INTO message_marks (message_id, reactions_json, feedback, updated_at) VALUES (?,?,?,?) "
            "ON CONFLICT(message_id) DO UPDATE SET reactions_json = excluded.reactions_json, "
            "feedback = excluded.feedback, updated_at = excluded.updated_at",
            (message_id, json.dumps(marks["reactions"], ensure_ascii=False), marks["feedback"], int(time.time())),
        )

    @staticmethod
    def _view(marks: Dict[str, Any]) -> Dict[str, Any]:
        reactions = [{"emoji": e, "count": len(a), "authors": a} for e, a in marks["reactions"].items() if a]
        return {"reactions": reactions, "feedback": marks["feedback"] or None}

    def toggle(self, thread_id: str, message_id: str, emoji: str, author: str) -> Optional[Dict[str, Any]]:
        if emoji not in REACTIONS:
            raise ValueError("unsupported_reaction")
        who = (author or "admin")[:AUTHOR_MAX]
        with self.store._lock, self.store._get_connection() as conn:
            if not self._owned(conn, thread_id, message_id):
                return None
            marks = self._load(conn, message_id)
            authors: List[str] = list(marks["reactions"].get(emoji, []))
            authors = [a for a in authors if a != who] if who in authors else [*authors, who]
            if authors:
                marks["reactions"][emoji] = authors
            else:
                marks["reactions"].pop(emoji, None)
            self._save(conn, message_id, marks)
        return self._view(marks)

    def set_feedback(self, thread_id: str, message_id: str, value: Optional[str]) -> Optional[Dict[str, Any]]:
        if value is not None and value not in FEEDBACK:
            raise ValueError("unsupported_feedback")
        with self.store._lock, self.store._get_connection() as conn:
            if not self._owned(conn, thread_id, message_id):
                return None
            marks = self._load(conn, message_id)
            marks["feedback"] = value or ""
            self._save(conn, message_id, marks)
        return self._view(marks)

    def decorate(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        ids = [m["id"] for m in messages]
        if not ids:
            return messages
        with self.store._lock, self.store._get_connection() as conn:
            rows = conn.execute(
                f"SELECT message_id, reactions_json, feedback FROM message_marks WHERE message_id IN ({','.join('?' * len(ids))})",
                ids,
            ).fetchall()
        marks = {r["message_id"]: self._view({"reactions": json.loads(r["reactions_json"] or "{}"), "feedback": r["feedback"]})
                 for r in rows}
        return [{**m, **marks.get(m["id"], {"reactions": [], "feedback": None})} for m in messages]
