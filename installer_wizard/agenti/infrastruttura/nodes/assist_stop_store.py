import sqlite3
import time
from contextlib import closing

from config import STATE_DIR


class AssistStopStore:
    def __init__(self, path=STATE_DIR / "assist-stops.sqlite3"):
        self.path = path

    def _connect(self):
        return sqlite3.connect(self.path, timeout=2)

    def record(self, key: str) -> None:
        now = time.time()
        with closing(self._connect()) as conn, conn:
            conn.execute("CREATE TABLE IF NOT EXISTS stops (key TEXT PRIMARY KEY, expires REAL NOT NULL)")
            conn.execute("DELETE FROM stops WHERE expires <= ?", (now,))
            conn.execute("INSERT OR REPLACE INTO stops VALUES (?, ?)", (key, now + 60))
            conn.execute("DELETE FROM stops WHERE key IN (SELECT key FROM stops ORDER BY expires DESC LIMIT -1 OFFSET 4096)")

    def contains(self, key: str) -> bool:
        with closing(self._connect()) as conn:
            exists = conn.execute("SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'stops'").fetchone()
            if exists is None:
                return False
            return conn.execute("SELECT 1 FROM stops WHERE key = ? AND expires > ?", (key, time.time())).fetchone() is not None
