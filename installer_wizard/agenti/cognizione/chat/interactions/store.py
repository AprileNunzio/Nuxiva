import json
import logging
import os
import re
import secrets
import sqlite3
import threading
import time
from contextlib import closing
from dataclasses import dataclass, field
from pathlib import Path

from cryptography.fernet import InvalidToken

from config import STATE_DIR
from sealed import SealedCipher, write_private

DB_PATH = STATE_DIR / "chat" / "interactions.db"
RETENTION = 30 * 86400
MAX_ROWS = 20000
PAGE_MAX = 200
CHANNELS = ("voice", "text")
ID = re.compile(r"^[0-9a-f]{16}$")
REF = re.compile(r"^[0-9a-f]{12}$")
TEXT_MAX = 4000
REPLY_MAX = 20000
SCHEMA = """
CREATE TABLE IF NOT EXISTS interactions (
    id TEXT PRIMARY KEY, at REAL NOT NULL, device TEXT NOT NULL, channel TEXT NOT NULL, voice_ref TEXT NOT NULL DEFAULT '',
    intent TEXT NOT NULL DEFAULT '', agent TEXT NOT NULL DEFAULT '', lang TEXT NOT NULL DEFAULT '',
    elapsed_ms INTEGER NOT NULL DEFAULT 0, directed INTEGER NOT NULL DEFAULT 1, payload BLOB NOT NULL)
"""
log = logging.getLogger("nuxiva.chat")


@dataclass
class Interaction:
    device: str
    channel: str
    said: str
    resolved: str = ""
    reply: str = ""
    intent: str = ""
    agent: str = ""
    lang: str = ""
    elapsed_ms: int = 0
    directed: bool = True
    voice_ref: str = ""
    speaker: str = ""
    score: float = 0.0
    reason: str = ""
    at: float = field(default_factory=time.time)


class InteractionStore:

    def __init__(self, path: Path | None = None) -> None:
        self.path = path or DB_PATH
        self.lock = threading.Lock()
        self._cipher: SealedCipher | None = None
        self.writes = 0

    def _key(self) -> Path:
        return self.path.with_name("interactions.key")

    def cipher(self) -> SealedCipher:
        if self._cipher is None:
            key = self._key()
            if not key.exists():
                key.parent.mkdir(parents=True, exist_ok=True)
                write_private(key, SealedCipher.generate_key())
            self._cipher = SealedCipher(key.read_bytes())
        return self._cipher

    def _connect(self) -> sqlite3.Connection:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fresh = not self.path.exists()
        conn = sqlite3.connect(self.path, timeout=5)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute(SCHEMA)
        conn.execute("CREATE INDEX IF NOT EXISTS interactions_at ON interactions (at)")
        if fresh:
            os.chmod(self.path, 0o600)
        return conn

    def add(self, item: Interaction) -> str:
        if item.channel not in CHANNELS or not item.said.strip():
            return ""
        entry_id = secrets.token_hex(8)
        payload = {"said": item.said[:TEXT_MAX], "resolved": item.resolved[:TEXT_MAX], "reply": item.reply[:REPLY_MAX],
                   "speaker": item.speaker[:60], "score": round(float(item.score), 3), "reason": item.reason[:120]}
        sealed = self.cipher().encrypt(json.dumps(payload, ensure_ascii=False).encode("utf-8"))
        ref = item.voice_ref if REF.match(item.voice_ref or "") else ""
        with self.lock, closing(self._connect()) as conn:
            conn.execute(
                "INSERT INTO interactions (id, at, device, channel, voice_ref, intent, agent, lang, elapsed_ms, directed, payload) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                (entry_id, item.at, item.device[:40], item.channel, ref, item.intent[:60], item.agent[:80], item.lang[:12],
                 max(0, int(item.elapsed_ms)), int(item.directed), sealed))
            self.writes += 1
            if self.writes % 100 == 1:
                self._prune(conn)
            conn.commit()
        return entry_id

    def _prune(self, conn: sqlite3.Connection) -> None:
        conn.execute("DELETE FROM interactions WHERE at < ?", (time.time() - RETENTION,))
        conn.execute("DELETE FROM interactions WHERE id NOT IN (SELECT id FROM interactions ORDER BY at DESC LIMIT ?)",
                     (MAX_ROWS,))

    def _row(self, row: sqlite3.Row) -> dict | None:
        try:
            payload = json.loads(self.cipher().decrypt(bytes(row["payload"])).decode("utf-8"))
        except (InvalidToken, UnicodeError, ValueError) as exc:
            log.warning("Interazione cifrata non leggibile: %s", type(exc).__name__)
            return None
        return {"id": row["id"], "at": row["at"], "device": row["device"], "channel": row["channel"],
                "voice_ref": row["voice_ref"], "intent": row["intent"], "agent": row["agent"], "lang": row["lang"],
                "elapsed_ms": row["elapsed_ms"], "directed": bool(row["directed"]), **payload}

    def list(self, limit: int = 50, before: float = 0.0, channel: str = "", query: str = "") -> list[dict]:
        clauses, args = [], []
        if before > 0:
            clauses.append("at < ?")
            args.append(before)
        if channel in CHANNELS:
            clauses.append("channel = ?")
            args.append(channel)
        where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
        size = max(1, min(PAGE_MAX, int(limit)))
        with self.lock, closing(self._connect()) as conn:
            rows = conn.execute(f"SELECT * FROM interactions {where} ORDER BY at DESC LIMIT ?",
                                (*args, 2000 if query else size)).fetchall()
        items = [item for item in (self._row(row) for row in rows) if item]
        needle = query.strip().casefold()
        if needle:
            items = [i for i in items if needle in i["said"].casefold() or needle in i["reply"].casefold()
                     or needle in i["resolved"].casefold()]
        return items[:size]

    def get(self, entry_id: str) -> dict | None:
        if not ID.match(entry_id or ""):
            return None
        with self.lock, closing(self._connect()) as conn:
            row = conn.execute("SELECT * FROM interactions WHERE id = ?", (entry_id,)).fetchone()
        return self._row(row) if row else None

    def delete(self, entry_id: str) -> bool:
        if not ID.match(entry_id or ""):
            return False
        with self.lock, closing(self._connect()) as conn:
            cur = conn.execute("DELETE FROM interactions WHERE id = ?", (entry_id,))
            conn.commit()
        return cur.rowcount == 1

    def purge(self) -> int:
        with self.lock, closing(self._connect()) as conn:
            cur = conn.execute("DELETE FROM interactions")
            conn.commit()
        return cur.rowcount


interactions = InteractionStore()
