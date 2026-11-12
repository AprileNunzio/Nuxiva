import hashlib
import os
import sqlite3
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

SHARDS = 256

SCHEMA = (
    "CREATE TABLE IF NOT EXISTS agents(id TEXT PRIMARY KEY, name TEXT NOT NULL, kind TEXT NOT NULL, category TEXT NOT NULL, "
    "state TEXT NOT NULL, priority INTEGER NOT NULL, origin TEXT NOT NULL, description TEXT NOT NULL, instructions BLOB NOT NULL, "
    "created INTEGER NOT NULL, updated INTEGER NOT NULL) WITHOUT ROWID",
    "CREATE INDEX IF NOT EXISTS agents_name ON agents(name COLLATE NOCASE)",
    "CREATE INDEX IF NOT EXISTS agents_state ON agents(state, id)",
    "CREATE TABLE IF NOT EXISTS links(agent_id TEXT NOT NULL, kind TEXT NOT NULL, ref TEXT NOT NULL, "
    "PRIMARY KEY(agent_id, kind, ref)) WITHOUT ROWID",
    "CREATE INDEX IF NOT EXISTS links_ref ON links(kind, ref, agent_id)",
    "CREATE TABLE IF NOT EXISTS counts(dim TEXT NOT NULL, val TEXT NOT NULL, n INTEGER NOT NULL, "
    "PRIMARY KEY(dim, val)) WITHOUT ROWID",
)


def shard_of(agent_id: str) -> int:
    return hashlib.sha256(agent_id.encode("utf-8")).digest()[0]


class Shards:
    def __init__(self, root: Path) -> None:
        self.root = root
        self._ready: set[int] = set()
        self._lock = threading.Lock()
        self.root.mkdir(parents=True, exist_ok=True)
        os.chmod(self.root, 0o700)

    def path(self, index: int) -> Path:
        return self.root / f"shard_{index:02x}.db"

    def exists(self, index: int) -> bool:
        return self.path(index).exists()

    def _prepare(self, index: int, connection: sqlite3.Connection) -> None:
        with self._lock:
            if index in self._ready:
                return
            connection.execute("PRAGMA journal_mode=WAL")
            for statement in SCHEMA:
                connection.execute(statement)
            connection.commit()
            os.chmod(self.path(index), 0o600)
            self._ready.add(index)

    @contextmanager
    def open(self, index: int) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.path(index), timeout=15, isolation_level=None)
        try:
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA synchronous=NORMAL")
            connection.execute("PRAGMA foreign_keys=ON")
            self._prepare(index, connection)
            yield connection
        finally:
            connection.close()

    @contextmanager
    def write(self, index: int) -> Iterator[sqlite3.Connection]:
        with self.open(index) as connection:
            connection.execute("BEGIN IMMEDIATE")
            try:
                yield connection
            except BaseException:
                connection.execute("ROLLBACK")
                raise
            connection.execute("COMMIT")
