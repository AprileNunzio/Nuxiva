import sqlite3
import threading
import time

from agenti.nvr.search import Query

SCHEMA = """CREATE TABLE IF NOT EXISTS events (
  id TEXT PRIMARY KEY, at REAL NOT NULL, camera TEXT NOT NULL, label TEXT NOT NULL, score REAL NOT NULL,
  source TEXT NOT NULL, zone TEXT NOT NULL DEFAULT '', text TEXT NOT NULL DEFAULT '', details TEXT NOT NULL DEFAULT '',
  camera_id TEXT NOT NULL DEFAULT '')"""
MAX_RESULTS = 200


class EventStore:
    def __init__(self, path) -> None:
        self.lock = threading.Lock()
        path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(str(path), check_same_thread=False)
        self.db.execute(SCHEMA)
        columns = {row[1] for row in self.db.execute("PRAGMA table_info(events)")}
        for name in ("details", "camera_id"):
            if name not in columns:
                self.db.execute(f"ALTER TABLE events ADD COLUMN {name} TEXT NOT NULL DEFAULT ''")
        self.db.commit()
        self.db.execute("CREATE INDEX IF NOT EXISTS ev_at ON events(at)")
        self.db.execute("CREATE INDEX IF NOT EXISTS ev_camera ON events(camera, at)")
        self.db.commit()

    def add(self, event: dict) -> bool:
        row = (str(event["id"])[:80], float(event["at"]), str(event["camera"])[:80], str(event["label"])[:40],
               max(0.0, min(1.0, float(event.get("score", 0.0)))), str(event.get("source", ""))[:20],
               str(event.get("zone", ""))[:80], str(event.get("text", ""))[:500], str(event.get("details", ""))[:4000],
               str(event.get("camera_id", ""))[:64])
        with self.lock:
            cur = self.db.execute("INSERT OR IGNORE INTO events (id, at, camera, label, score, source, zone, text, details, camera_id) VALUES (?,?,?,?,?,?,?,?,?,?)", row)
            self.db.commit()
            return cur.rowcount == 1

    def search(self, query: Query, limit: int = 50) -> list[dict]:
        sql = "SELECT id, at, camera, label, score, source, zone, text, details, camera_id FROM events WHERE at >= ? AND at <= ?"
        args: list = [query.since, query.until]
        if query.labels:
            sql += f" AND label IN ({','.join('?' * len(query.labels))})"
            args += sorted(query.labels)
        for term in query.terms:
            sql += " AND (camera LIKE ? ESCAPE '!' OR zone LIKE ? ESCAPE '!' OR text LIKE ? ESCAPE '!' OR details LIKE ? ESCAPE '!')"
            like = "%" + term.replace("!", "!!").replace("%", "!%").replace("_", "!_") + "%"
            args += [like, like, like, like]
        sql += " ORDER BY at DESC LIMIT ?"
        args.append(max(1, min(MAX_RESULTS, limit)))
        with self.lock:
            rows = self.db.execute(sql, args).fetchall()
        keys = ("id", "at", "camera", "label", "score", "source", "zone", "text", "details", "camera_id")
        return [dict(zip(keys, r)) for r in rows]

    def get(self, event_id: str) -> dict | None:
        with self.lock:
            row = self.db.execute(
                "SELECT id, at, camera, label, score, source, zone, text, details FROM events WHERE id = ?",
                (str(event_id)[:80],)
            ).fetchone()
        if not row:
            return None
        keys = ("id", "at", "camera", "label", "score", "source", "zone", "text", "details")
        return dict(zip(keys, row))

    def camera_times(self, since: float, limit: int = 200_000) -> list[tuple[str, int]]:
        with self.lock:
            rows = self.db.execute("SELECT camera_id, at FROM events WHERE at >= ? AND camera_id != '' ORDER BY at DESC LIMIT ?",
                                   (since, limit)).fetchall()
        return [(cid, int(at * 1000)) for cid, at in rows]

    def between(self, camera_id: str, since: float, until: float, limit: int = 2000) -> list[dict]:
        keys = ("id", "at", "camera", "label", "score", "source", "zone", "text", "details", "camera_id")
        with self.lock:
            rows = self.db.execute(f"SELECT {', '.join(keys)} FROM events WHERE camera_id = ? AND at >= ? AND at <= ? "
                                   "ORDER BY at LIMIT ?", (camera_id, since, until, max(1, min(20_000, limit)))).fetchall()
        return [dict(zip(keys, r)) for r in rows]

    def counts(self, since: float) -> dict:
        with self.lock:
            rows = self.db.execute("SELECT label, COUNT(*) FROM events WHERE at >= ? GROUP BY label", (since,)).fetchall()
        return {label: n for label, n in rows}

    def prune(self, days: int) -> int:
        with self.lock:
            cur = self.db.execute("DELETE FROM events WHERE at < ?", (time.time() - days * 86400,))
            self.db.commit()
            return cur.rowcount

    def clear(self) -> None:
        with self.lock:
            self.db.execute("DELETE FROM events")
            self.db.commit()

    def close(self) -> None:
        with self.lock:
            self.db.close()
