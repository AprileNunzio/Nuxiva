import json
import os
import re
import sqlite3
import threading
from pathlib import Path

MAX_LIMIT = 100
MAX_KEY = 120
MAX_KIND = 32
MAX_META = 16 * 1024
MAX_TAGS = 48
MAX_QUERY_TOKENS = 8
MAX_TOKEN = 32
CANDIDATES = 2000
DIGEST = re.compile(r"^[0-9a-f]{64}$")
SCHEMA = """
CREATE TABLE IF NOT EXISTS creations (
    id INTEGER PRIMARY KEY, key TEXT NOT NULL UNIQUE, digest TEXT NOT NULL, kind TEXT NOT NULL, meta TEXT NOT NULL,
    created INTEGER NOT NULL, last INTEGER NOT NULL, uses INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS creations_last ON creations(last);
CREATE INDEX IF NOT EXISTS creations_digest ON creations(digest);
CREATE VIRTUAL TABLE IF NOT EXISTS creations_fts USING fts5(
    key, tags, content='', contentless_delete=1, tokenize='unicode61 remove_diacritics 2', prefix='2 3'
);"""
COLUMNS = "key, digest, kind, meta, created, last, uses"


def _native():
    if os.environ.get("NUXIVA_NATIVE", "auto").strip() == "0":
        return None
    try:
        import nuxiva_native
    except ImportError:
        return None
    return nuxiva_native if hasattr(nuxiva_native, "RustCreationArchive") else None


def tokens(text: str, limit: int = MAX_TAGS) -> list[str]:
    out: list[str] = []
    for raw in re.split(r"[^\w]|_", str(text)):
        if raw and len(out) < limit:
            word = raw.lower()[:MAX_TOKEN]
            if word not in out:
                out.append(word)
    return out


def shard(digest: str) -> str | None:
    return f"{digest[:2]}/{digest[2:4]}/{digest}" if isinstance(digest, str) and DIGEST.match(digest) else None


def _check(entry: dict) -> None:
    key, digest, kind, meta = entry.get("key", ""), entry.get("digest", ""), entry.get("kind", ""), entry.get("meta", "")
    if not isinstance(key, str) or not key or len(key) > MAX_KEY:
        raise ValueError("invalid key")
    if shard(digest) is None:
        raise ValueError("invalid digest")
    if not isinstance(kind, str) or not kind or len(kind) > MAX_KIND or not isinstance(meta, str) or len(meta.encode()) > MAX_META:
        raise ValueError("invalid entry")


def _row(row) -> dict:
    return dict(zip(("key", "digest", "kind", "meta", "created", "last", "uses"), row))


class PyArchive:
    def __init__(self, path: str) -> None:
        self.lock = threading.RLock()
        self.conn = sqlite3.connect(path, check_same_thread=False, isolation_level=None)
        os.chmod(path, 0o600)
        self.conn.executescript("PRAGMA journal_mode=WAL; PRAGMA synchronous=NORMAL; PRAGMA trusted_schema=OFF; PRAGMA secure_delete=ON;")
        self.conn.executescript(SCHEMA)

    def put(self, entry: dict, now: int) -> dict:
        _check(entry)
        tags = [t for tag in entry.get("tags", [])[:MAX_TAGS] for t in tokens(tag)]
        words = " ".join(tokens(entry["key"]))
        with self.lock:
            self.conn.execute("BEGIN")
            try:
                found = self.conn.execute("SELECT id, created, uses FROM creations WHERE key = ?", (entry["key"],)).fetchone()
                if found:
                    row_id, created, uses = found
                    self.conn.execute("UPDATE creations SET digest=?, kind=?, meta=?, last=? WHERE id=?",
                                      (entry["digest"], entry["kind"], entry["meta"], now, row_id))
                    self.conn.execute("DELETE FROM creations_fts WHERE rowid = ?", (row_id,))
                else:
                    cursor = self.conn.execute(
                        "INSERT INTO creations(key, digest, kind, meta, created, last, uses) VALUES (?,?,?,?,?,?,1)",
                        (entry["key"], entry["digest"], entry["kind"], entry["meta"], now, now))
                    row_id, created, uses = cursor.lastrowid, now, 1
                self.conn.execute("INSERT INTO creations_fts(rowid, key, tags) VALUES (?,?,?)", (row_id, words, " ".join(tags)))
                self.conn.execute("COMMIT")
            except BaseException:
                self.conn.execute("ROLLBACK")
                raise
        return {"key": entry["key"], "digest": entry["digest"], "kind": entry["kind"], "meta": entry["meta"], "created": created,
                "last": now, "uses": uses}

    def lookup(self, key: str, now: int) -> dict | None:
        with self.lock:
            self.conn.execute("UPDATE creations SET uses = uses + 1, last = ? WHERE key = ?", (now, key))
            row = self.conn.execute(f"SELECT {COLUMNS} FROM creations WHERE key = ?", (key,)).fetchone()
        return _row(row) if row else None

    def search(self, query: str, limit: int) -> list[dict]:
        words = tokens(query, MAX_QUERY_TOKENS)
        if not words:
            return []
        expression = " OR ".join(f'"{w}"*' for w in words)
        with self.lock:
            rows = self.conn.execute(
                "SELECT c.key, c.digest, c.kind, c.uses FROM (SELECT rowid AS id, rank FROM creations_fts WHERE creations_fts MATCH ? "
                f"LIMIT {CANDIDATES}) f JOIN creations c ON c.id = f.id ORDER BY f.rank, c.uses DESC, c.key LIMIT ?",
                (expression, max(1, min(MAX_LIMIT, limit)))).fetchall()
        return [dict(zip(("key", "digest", "kind", "uses"), row)) for row in rows]

    def recent(self, limit: int) -> list[dict]:
        with self.lock:
            rows = self.conn.execute(f"SELECT {COLUMNS} FROM creations ORDER BY last DESC, key LIMIT ?", (max(1, min(MAX_LIMIT, limit)),)).fetchall()
        return [_row(r) for r in rows]

    def count(self) -> int:
        with self.lock:
            return self.conn.execute("SELECT COUNT(*) FROM creations").fetchone()[0]

    def evict(self, keep: int) -> list[str]:
        with self.lock:
            self.conn.execute("BEGIN")
            try:
                victims = self.conn.execute("SELECT id, digest FROM creations ORDER BY last DESC, key LIMIT -1 OFFSET ?", (keep,)).fetchall()
                for row_id, _ in victims:
                    self.conn.execute("DELETE FROM creations_fts WHERE rowid = ?", (row_id,))
                    self.conn.execute("DELETE FROM creations WHERE id = ?", (row_id,))
                orphans: list[str] = []
                for _, digest in victims:
                    used = self.conn.execute("SELECT COUNT(*) FROM creations WHERE digest = ?", (digest,)).fetchone()[0]
                    if used == 0 and digest not in orphans:
                        orphans.append(digest)
                self.conn.execute("COMMIT")
            except BaseException:
                self.conn.execute("ROLLBACK")
                raise
        return orphans


class RustArchive:
    def __init__(self, lib, path: str) -> None:
        self.inner = lib.RustCreationArchive(path)

    def put(self, entry: dict, now: int) -> dict:
        _check(entry)
        return json.loads(self.inner.put(json.dumps(entry, ensure_ascii=False), now))

    def lookup(self, key: str, now: int) -> dict | None:
        found = self.inner.lookup(key, now)
        return json.loads(found) if found is not None else None

    def search(self, query: str, limit: int) -> list[dict]:
        return json.loads(self.inner.search(query, max(1, min(MAX_LIMIT, limit))))

    def recent(self, limit: int) -> list[dict]:
        return json.loads(self.inner.recent(max(1, min(MAX_LIMIT, limit))))

    def count(self) -> int:
        return self.inner.count()

    def evict(self, keep: int) -> list[str]:
        return list(self.inner.evict(max(0, keep)))


def open_archive(path: Path | str, native: bool = True):
    lib = _native() if native else None
    return RustArchive(lib, str(path)) if lib is not None else PyArchive(str(path))
