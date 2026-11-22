import json
import sqlite3
import threading
import time
from pathlib import Path
from typing import Any, List, Optional, Tuple
from config import STATE_DIR
from .models import Project, Thread, Message, Artifact, Attachment, MemoryFact


class StudioStore:
    _lock = threading.Lock()

    def __init__(self, db_path: Optional[Path] = None) -> None:
        if db_path is None:
            db_path = Path(STATE_DIR) / "ai_studio.db"
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), timeout=15.0)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_schema(self) -> None:
        with self._lock, self._get_connection() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS projects (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT NOT NULL DEFAULT '',
                    instructions TEXT NOT NULL DEFAULT '',
                    smb_folder TEXT NOT NULL DEFAULT '',
                    created_at INTEGER NOT NULL,
                    updated_at INTEGER NOT NULL
                );

                CREATE TABLE IF NOT EXISTS threads (
                    id TEXT PRIMARY KEY,
                    project_id TEXT,
                    title TEXT NOT NULL,
                    pinned INTEGER NOT NULL DEFAULT 0,
                    model_mode TEXT NOT NULL DEFAULT 'fast',
                    created_at INTEGER NOT NULL,
                    updated_at INTEGER NOT NULL,
                    FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE SET NULL
                );

                CREATE TABLE IF NOT EXISTS messages (
                    id TEXT PRIMARY KEY,
                    thread_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    thought TEXT NOT NULL DEFAULT '',
                    artifacts_json TEXT NOT NULL DEFAULT '[]',
                    attachments_json TEXT NOT NULL DEFAULT '[]',
                    memory_json TEXT NOT NULL DEFAULT '[]',
                    created_at INTEGER NOT NULL,
                    cached INTEGER NOT NULL DEFAULT 0,
                    FOREIGN KEY(thread_id) REFERENCES threads(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS learned_memory (
                    id TEXT PRIMARY KEY,
                    source TEXT NOT NULL,
                    content TEXT NOT NULL,
                    speaker TEXT NOT NULL DEFAULT '',
                    timestamp INTEGER NOT NULL,
                    tags_json TEXT NOT NULL DEFAULT '[]'
                );

                CREATE INDEX IF NOT EXISTS idx_threads_project ON threads(project_id);
                CREATE INDEX IF NOT EXISTS idx_messages_thread ON messages(thread_id);
                CREATE INDEX IF NOT EXISTS idx_learned_ts ON learned_memory(timestamp);
                """
            )
            try:
                conn.execute("ALTER TABLE messages ADD COLUMN cached INTEGER NOT NULL DEFAULT 0")
            except Exception:
                pass

    def list_projects(self) -> List[Project]:
        query = """
            SELECT p.*, COUNT(t.id) as thread_count
            FROM projects p
            LEFT JOIN threads t ON t.project_id = p.id
            GROUP BY p.id
            ORDER BY p.updated_at DESC
        """
        with self._lock, self._get_connection() as conn:
            rows = conn.execute(query).fetchall()
            return [
                Project(
                    id=row["id"],
                    name=row["name"],
                    description=row["description"],
                    instructions=row["instructions"],
                    smb_folder=row["smb_folder"],
                    created_at=row["created_at"],
                    updated_at=row["updated_at"],
                    thread_count=row["thread_count"],
                )
                for row in rows
            ]

    def get_project(self, project_id: str) -> Optional[Project]:
        query = """
            SELECT p.*, COUNT(t.id) as thread_count
            FROM projects p
            LEFT JOIN threads t ON t.project_id = p.id
            WHERE p.id = ?
            GROUP BY p.id
        """
        with self._lock, self._get_connection() as conn:
            row = conn.execute(query, (project_id,)).fetchone()
            if not row:
                return None
            return Project(
                id=row["id"],
                name=row["name"],
                description=row["description"],
                instructions=row["instructions"],
                smb_folder=row["smb_folder"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
                thread_count=row["thread_count"],
            )

    def save_project(self, project: Project) -> None:
        with self._lock, self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO projects (id, name, description, instructions, smb_folder, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    name = excluded.name,
                    description = excluded.description,
                    instructions = excluded.instructions,
                    smb_folder = excluded.smb_folder,
                    updated_at = excluded.updated_at
                """,
                (
                    project.id,
                    project.name,
                    project.description,
                    project.instructions,
                    project.smb_folder,
                    project.created_at,
                    project.updated_at,
                ),
            )

    def delete_project(self, project_id: str) -> None:
        with self._lock, self._get_connection() as conn:
            conn.execute("DELETE FROM projects WHERE id = ?", (project_id,))

    def list_threads(self, project_id: Optional[str] = None) -> List[Thread]:
        query = """
            SELECT t.*, COUNT(m.id) as message_count
            FROM threads t
            LEFT JOIN messages m ON m.thread_id = t.id
        """
        params: Tuple[Any, ...] = ()
        if project_id:
            query += " WHERE t.project_id = ?"
            params = (project_id,)
        query += " GROUP BY t.id ORDER BY t.pinned DESC, t.updated_at DESC"
        with self._lock, self._get_connection() as conn:
            rows = conn.execute(query, params).fetchall()
            return [
                Thread(
                    id=row["id"],
                    project_id=row["project_id"],
                    title=row["title"],
                    pinned=bool(row["pinned"]),
                    model_mode=row["model_mode"],
                    created_at=row["created_at"],
                    updated_at=row["updated_at"],
                    message_count=row["message_count"],
                )
                for row in rows
            ]

    def get_thread(self, thread_id: str) -> Optional[Thread]:
        query = """
            SELECT t.*, COUNT(m.id) as message_count
            FROM threads t
            LEFT JOIN messages m ON m.thread_id = t.id
            WHERE t.id = ?
            GROUP BY t.id
        """
        with self._lock, self._get_connection() as conn:
            row = conn.execute(query, (thread_id,)).fetchone()
            if not row:
                return None
            return Thread(
                id=row["id"],
                project_id=row["project_id"],
                title=row["title"],
                pinned=bool(row["pinned"]),
                model_mode=row["model_mode"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
                message_count=row["message_count"],
            )

    def save_thread(self, thread: Thread) -> None:
        with self._lock, self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO threads (id, project_id, title, pinned, model_mode, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    project_id = excluded.project_id,
                    title = excluded.title,
                    pinned = excluded.pinned,
                    model_mode = excluded.model_mode,
                    updated_at = excluded.updated_at
                """,
                (
                    thread.id,
                    thread.project_id,
                    thread.title,
                    1 if thread.pinned else 0,
                    thread.model_mode,
                    thread.created_at,
                    thread.updated_at,
                ),
            )

    def fork_thread(self, thread_id: str, new_title: Optional[str] = None) -> Optional[Thread]:
        parent = self.get_thread(thread_id)
        if not parent:
            return None
        now = int(time.time())
        import uuid
        new_id = f"th_{now}_{uuid.uuid4().hex[:6]}"
        title = new_title or f"{parent.title} (Ramo)"
        new_thread = Thread(
            id=new_id,
            project_id=parent.project_id,
            title=title,
            pinned=False,
            model_mode=parent.model_mode,
            created_at=now,
            updated_at=now,
        )
        self.save_thread(new_thread)

        messages = self.list_messages(thread_id)
        for m in messages:
            forked_msg = Message(
                id=f"msg_f_{now}_{uuid.uuid4().hex[:6]}",
                thread_id=new_id,
                role=m.role,
                content=m.content,
                thought=m.thought,
                artifacts=m.artifacts,
                attachments=m.attachments,
                memory_recalls=m.memory_recalls,
                created_at=m.created_at,
                cached=m.cached,
            )
            self.add_message(forked_msg)

        return self.get_thread(new_id)

    def delete_thread(self, thread_id: str) -> None:
        with self._lock, self._get_connection() as conn:
            conn.execute("DELETE FROM messages WHERE thread_id = ?", (thread_id,))
            conn.execute("DELETE FROM threads WHERE id = ?", (thread_id,))

    def list_messages(self, thread_id: str) -> List[Message]:
        with self._lock, self._get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM messages WHERE thread_id = ? ORDER BY created_at ASC",
                (thread_id,),
            ).fetchall()
            results: List[Message] = []
            for row in rows:
                raw_art = json.loads(row["artifacts_json"] or "[]")
                raw_att = json.loads(row["attachments_json"] or "[]")
                raw_mem = json.loads(row["memory_json"] or "[]")
                artifacts = [
                    Artifact(
                        id=a.get("id", ""),
                        identifier=a.get("identifier", ""),
                        title=a.get("title", ""),
                        kind=a.get("kind", ""),
                        language=a.get("language", ""),
                        content=a.get("content", ""),
                    )
                    for a in raw_art
                ]
                attachments = [
                    Attachment(
                        id=a.get("id", ""),
                        name=a.get("name", ""),
                        size=a.get("size", 0),
                        mime_type=a.get("mime_type", ""),
                        kind=a.get("kind", ""),
                        path=a.get("path", ""),
                        data_url=a.get("data_url"),
                    )
                    for a in raw_att
                ]
                memory_recalls = [
                    MemoryFact(
                        id=m.get("id", ""),
                        source=m.get("source", ""),
                        content=m.get("content", ""),
                        speaker=m.get("speaker", ""),
                        timestamp=m.get("timestamp", 0),
                        tags=m.get("tags", []),
                    )
                    for m in raw_mem
                ]
                results.append(
                    Message(
                        id=row["id"],
                        thread_id=row["thread_id"],
                        role=row["role"],
                        content=row["content"],
                        thought=row["thought"],
                        artifacts=artifacts,
                        attachments=attachments,
                        memory_recalls=memory_recalls,
                        created_at=row["created_at"],
                        cached=bool(row["cached"]) if "cached" in row.keys() else False,
                    )
                )
            return results

    def add_message(self, message: Message) -> None:
        with self._lock, self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO messages (id, thread_id, role, content, thought, artifacts_json, attachments_json, memory_json, created_at, cached)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    message.id,
                    message.thread_id,
                    message.role,
                    message.content,
                    message.thought,
                    json.dumps([a.to_dict() for a in message.artifacts]),
                    json.dumps([a.to_dict() for a in message.attachments]),
                    json.dumps([m.to_dict() for m in message.memory_recalls]),
                    message.created_at or int(time.time()),
                    1 if message.cached else 0,
                ),
            )
            conn.execute(
                "UPDATE threads SET updated_at = ? WHERE id = ?",
                (int(time.time()), message.thread_id),
            )

    def add_memory(self, fact: MemoryFact) -> None:
        with self._lock, self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO learned_memory (id, source, content, speaker, timestamp, tags_json)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    content = excluded.content,
                    speaker = excluded.speaker,
                    timestamp = excluded.timestamp,
                    tags_json = excluded.tags_json
                """,
                (
                    fact.id,
                    fact.source,
                    fact.content,
                    fact.speaker,
                    fact.timestamp,
                    json.dumps(fact.tags),
                ),
            )

    def get_all_memory(self) -> List[MemoryFact]:
        with self._lock, self._get_connection() as conn:
            rows = conn.execute("SELECT * FROM learned_memory ORDER BY timestamp DESC LIMIT 200").fetchall()
            return [
                MemoryFact(
                    id=row["id"],
                    source=row["source"],
                    content=row["content"],
                    speaker=row["speaker"],
                    timestamp=row["timestamp"],
                    tags=json.loads(row["tags_json"] or "[]"),
                )
                for row in rows
            ]
