import sqlite3
import threading
import time

from config import STATE_DIR

FILE = STATE_DIR / "habits.db"
KEEP_DAYS = 60
ACTIONABLE = {"light", "switch", "cover", "climate", "media_player", "fan", "lock", "input_boolean"}
WATCHED = {"binary_sensor"}


class Journal:
    def __init__(self, path=FILE) -> None:
        self.lock = threading.Lock()
        self.db = sqlite3.connect(str(path), check_same_thread=False)
        self.db.execute("CREATE TABLE IF NOT EXISTS events (at REAL, entity TEXT, state TEXT, wd INTEGER, mins INTEGER, "
                        "people INTEGER, sun INTEGER, kind TEXT)")
        if "who" not in {row[1] for row in self.db.execute("PRAGMA table_info(events)")}:
            self.db.execute("ALTER TABLE events ADD COLUMN who TEXT NOT NULL DEFAULT ''")
        self.db.execute("CREATE INDEX IF NOT EXISTS ev_entity ON events(entity, state, at)")
        self.db.execute("CREATE INDEX IF NOT EXISTS ev_who ON events(who, at)")
        self.db.execute("CREATE INDEX IF NOT EXISTS ev_kind ON events(kind, at)")
        self.db.commit()

    def add(self, at: float, entity: str, state: str, people: int, sun_up: bool, kind: str, who: str = "") -> None:
        t = time.localtime(at)
        with self.lock:
            self.db.execute("INSERT INTO events (at, entity, state, wd, mins, people, sun, kind, who) VALUES (?,?,?,?,?,?,?,?,?)",
                            (at, entity, str(state), t.tm_wday, t.tm_hour * 60 + t.tm_min, people, int(sun_up), kind, who))
            self.db.commit()

    def rows_for(self, who: str, since: float) -> list[tuple]:
        with self.lock:
            return self.db.execute("SELECT at, entity, state, wd, mins, people, sun, kind FROM events WHERE who = ? AND at >= ? "
                                   "ORDER BY at", (who, since)).fetchall()

    def forget(self, who: str) -> int:
        with self.lock:
            cursor = self.db.execute("DELETE FROM events WHERE who = ?", (who,))
            self.db.commit()
            return cursor.rowcount

    def rows(self, since: float, kind: str | None = None) -> list[tuple]:
        q = "SELECT at, entity, state, wd, mins, people, sun, kind FROM events WHERE at >= ?"
        args: list = [since]
        if kind:
            q += " AND kind = ?"
            args.append(kind)
        with self.lock:
            return self.db.execute(q + " ORDER BY at", args).fetchall()

    def count(self) -> int:
        with self.lock:
            return self.db.execute("SELECT COUNT(*) FROM events").fetchone()[0]

    def prune(self) -> None:
        with self.lock:
            self.db.execute("DELETE FROM events WHERE at < ?", (time.time() - KEEP_DAYS * 86400,))
            self.db.commit()
