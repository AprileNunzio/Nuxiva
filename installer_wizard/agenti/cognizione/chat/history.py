import logging
import os
from contextlib import contextmanager
import sqlite3
import threading
import time
from pathlib import Path

from cryptography.fernet import InvalidToken

from config import STATE_DIR
from sealed import SealedCipher, write_private

HISTORY_DB = STATE_DIR / "chat" / "dialogue.db"
RETENTION = 7 * 86400
SEALED = "s1:"
log = logging.getLogger("nuxiva.chat")


class HistoryStore:

    def __init__(self, path: Path | None = None) -> None:
        self.path = path
        self.lock = threading.Lock()
        self.broken = False
        self.writes = 0
        self._cipher: SealedCipher | None = None
        self._unreadable = False

    def _db(self) -> Path:
        return self.path or HISTORY_DB

    def _key(self) -> Path:
        return self._db().with_name("dialogue.key")

    def cipher(self) -> SealedCipher:
        if self._cipher is None:
            key = self._key()
            if not key.exists():
                key.parent.mkdir(parents=True, exist_ok=True)
                write_private(key, SealedCipher.generate_key())
            self._cipher = SealedCipher(key.read_bytes())
        return self._cipher

    def seal(self, value: str) -> str:
        return SEALED + self.cipher().encrypt(value.encode("utf-8")).decode("ascii")

    def open(self, value: str) -> str | None:
        if not value.startswith(SEALED):
            return value
        try:
            return self.cipher().decrypt(value[len(SEALED):].encode("ascii")).decode("utf-8")
        except (InvalidToken, UnicodeError, ValueError, OSError) as exc:
            if not self._unreadable:
                self._unreadable = True
                log.warning("Scambi cifrati non leggibili con la chiave attuale: %s", exc)
            return None

    def _connect(self) -> sqlite3.Connection:
        path = self._db()
        path.parent.mkdir(parents=True, exist_ok=True)
        fresh = not path.exists()
        conn = sqlite3.connect(path, timeout=5)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("CREATE TABLE IF NOT EXISTS turns (device TEXT NOT NULL, text TEXT NOT NULL, reply TEXT NOT NULL, "
                     "intent TEXT NOT NULL, at REAL NOT NULL, who TEXT NOT NULL DEFAULT '')")
        if "who" not in {row[1] for row in conn.execute("PRAGMA table_info(turns)")}:
            conn.execute("ALTER TABLE turns ADD COLUMN who TEXT NOT NULL DEFAULT ''")
        conn.execute("CREATE INDEX IF NOT EXISTS turns_device_at ON turns (device, at)")
        if fresh:
            os.chmod(path, 0o600)
        return conn

    @contextmanager
    def _session(self):
        conn = self._connect()
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def add(self, device: str, text: str, reply: str, intent: str, at: float, who: str = "") -> None:
        if self.broken:
            return
        try:
            with self.lock, self._session() as conn:
                sealed = (self.seal(text), self.seal(reply), self.seal(who) if who else "")
                conn.execute("INSERT INTO turns (device, text, reply, intent, at, who) VALUES (?, ?, ?, ?, ?, ?)",
                             (device, sealed[0], sealed[1], intent, at, sealed[2]))
                self.writes += 1
                if self.writes % 50 == 1:
                    conn.execute("DELETE FROM turns WHERE at < ?", (time.time() - RETENTION,))
        except (sqlite3.Error, OSError, ValueError, TypeError) as exc:
            self.broken = True
            log.warning("Storia della conversazione solo in memoria: %s", exc)

    def recent(self, device: str, since: float, limit: int) -> list[tuple[str, str, str, float, str]]:
        if self.broken:
            return []
        try:
            with self.lock, self._session() as conn:
                rows = conn.execute("SELECT text, reply, intent, at, who FROM turns WHERE device = ? AND at >= ? "
                                    "ORDER BY at DESC LIMIT ?", (device, since, limit)).fetchall()
            opened = [(self.open(t), self.open(r), i, a, self.open(w) or "") for t, r, i, a, w in rows]
        except (sqlite3.Error, OSError, ValueError, TypeError) as exc:
            self.broken = True
            log.warning("Storia della conversazione non leggibile: %s", exc)
            return []
        return [row for row in reversed(opened) if row[0] is not None and row[1] is not None]

    def recent_all(self, since: float, limit: int) -> list[tuple[str, str]]:
        if self.broken:
            return []
        try:
            with self.lock, self._session() as conn:
                rows = conn.execute("SELECT text, reply FROM turns WHERE at >= ? ORDER BY at DESC LIMIT ?", (since, limit)).fetchall()
            opened = [(self.open(t), self.open(r)) for t, r in rows]
        except (sqlite3.Error, OSError, ValueError, TypeError) as exc:
            log.warning("Storia della conversazione non leggibile: %s", exc)
            return []
        return [row for row in reversed(opened) if row[0] is not None and row[1] is not None]

    def forget(self, device: str = "") -> int:
        try:
            with self.lock, self._session() as conn:
                cursor = conn.execute("DELETE FROM turns WHERE device = ?", (device,)) if device else conn.execute("DELETE FROM turns")
                return cursor.rowcount
        except (sqlite3.Error, OSError, ValueError) as exc:
            log.warning("Storia della conversazione non cancellata: %s", exc)
            return 0


history = HistoryStore()
