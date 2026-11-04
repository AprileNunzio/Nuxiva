import contextlib
import json
import sqlite3
import threading
import time
import uuid

from config import STATE_DIR
from sealed import SealedFile

from features.people import private_store

FILE = STATE_DIR / "wellbeing.db"
READING_EVERY = 30.0
RETENTION_DAYS = 180
MAX_TEXT = 4000
SCHEMA = """
create table if not exists consent(slug text primary key, active integer not null, at real not null);
create table if not exists baseline(slug text primary key, payload text not null);
create table if not exists readings(id integer primary key autoincrement, slug text not null, at real not null,
  arousal real not null, area text not null, payload text not null);
create index if not exists readings_slug_at on readings(slug, at);
create table if not exists sessions(id text primary key, slug text not null, stage text not null, phase text not null,
  started real not null, central_at real, ended real, lang text not null, closing integer not null default 0,
  mood_before integer, mood_after integer, risk integer not null default 0);
create index if not exists sessions_slug on sessions(slug, started);
create table if not exists turns(id integer primary key autoincrement, session text not null references sessions(id) on delete cascade,
  at real not null, role text not null, phase text not null, text text not null);
create table if not exists summaries(session text primary key references sessions(id) on delete cascade, payload text not null);
create table if not exists plan(slug text primary key, stage text not null, next_at real, concluded integer not null default 0);
"""
_lock = threading.RLock()
_last_reading: dict[str, float] = {}
_consent: dict[str, bool] = {}
_ready: set[str] = set()


def _cipher():
    return SealedFile(FILE.with_suffix(".cipher"), private_store.KEY_FILE).cipher()


def seal(value) -> str:
    return _cipher().encrypt(json.dumps(value, ensure_ascii=False).encode()).decode()


def unseal(token: str):
    return json.loads(_cipher().decrypt(token.encode()))


@contextlib.contextmanager
def connect():
    FILE.parent.mkdir(parents=True, exist_ok=True)
    with _lock:
        db = sqlite3.connect(FILE, timeout=10)
        try:
            db.row_factory = sqlite3.Row
            db.execute("pragma journal_mode=wal")
            db.execute("pragma secure_delete=on")
            db.execute("pragma foreign_keys=on")
            if str(FILE) not in _ready:
                db.executescript(SCHEMA)
                _ready.add(str(FILE))
            yield db
            db.commit()
        finally:
            db.close()
        with contextlib.suppress(OSError):
            FILE.chmod(0o600)


def consent(slug: str) -> bool:
    if slug not in _consent:
        with connect() as db:
            row = db.execute("select active from consent where slug=?", (slug,)).fetchone()
        _consent[slug] = bool(row and row["active"])
    return _consent[slug]


def set_consent(slug: str, active: bool) -> None:
    with connect() as db:
        db.execute("insert into consent(slug, active, at) values(?,?,?) on conflict(slug) do update set active=excluded.active, at=excluded.at",
                   (slug, int(active), time.time()))
    _consent[slug] = bool(active)


def load_baseline(slug: str) -> dict | None:
    with connect() as db:
        row = db.execute("select payload from baseline where slug=?", (slug,)).fetchone()
    return unseal(row["payload"]) if row else None


def save_baseline(slug: str, state: dict) -> None:
    with connect() as db:
        db.execute("insert into baseline(slug, payload) values(?,?) on conflict(slug) do update set payload=excluded.payload", (slug, seal(state)))


def add_reading(slug: str, reading: dict, now: float) -> bool:
    if now - _last_reading.get(slug, 0.0) < READING_EVERY:
        return False
    _last_reading[slug] = now
    detail = {k: reading[k] for k in ("valence", "brow_tension", "mimic", "lip_tone") if k in reading}
    with connect() as db:
        db.execute("insert into readings(slug, at, arousal, area, payload) values(?,?,?,?,?)",
                   (slug, now, reading["arousal"], reading["area"], seal(detail)))
        db.execute("delete from readings where at < ?", (now - RETENTION_DAYS * 86400,))
    return True


def readings(slug: str, since: float = 0.0) -> list[dict]:
    with connect() as db:
        rows = db.execute("select at, arousal, area, payload from readings where slug=? and at>=? order by at", (slug, since)).fetchall()
    return [{"at": r["at"], "arousal": r["arousal"], "area": r["area"], **unseal(r["payload"])} for r in rows]


def new_session(slug: str, stage: str, lang: str, mood_before, now: float) -> dict:
    sid = uuid.uuid4().hex[:16]
    with connect() as db:
        db.execute("insert into sessions(id, slug, stage, phase, started, lang, mood_before) values(?,?,?,?,?,?,?)",
                   (sid, slug, stage, "opening", now, lang, mood_before))
    return session(sid)


def session(sid: str) -> dict | None:
    with connect() as db:
        row = db.execute("select * from sessions where id=?", (sid,)).fetchone()
    return dict(row) if row else None


def update_session(sid: str, **fields) -> None:
    allowed = {"phase", "central_at", "ended", "closing", "mood_after", "risk"}
    names = [k for k in fields if k in allowed]
    if not names:
        return
    with connect() as db:
        db.execute(f"update sessions set {', '.join(f'{n}=?' for n in names)} where id=?", (*[fields[n] for n in names], sid))


def sessions(slug: str, limit: int = 100) -> list[dict]:
    with connect() as db:
        rows = db.execute("select * from sessions where slug=? order by started desc limit ?", (slug, limit)).fetchall()
    return [dict(r) for r in rows]


def open_session(slug: str) -> dict | None:
    with connect() as db:
        row = db.execute("select * from sessions where slug=? and ended is null order by started desc limit 1", (slug,)).fetchone()
    return dict(row) if row else None


def add_turn(sid: str, role: str, phase: str, text: str, now: float) -> None:
    with connect() as db:
        db.execute("insert into turns(session, at, role, phase, text) values(?,?,?,?,?)", (sid, now, role, phase, seal(str(text)[:MAX_TEXT])))


def turns(sid: str) -> list[dict]:
    with connect() as db:
        rows = db.execute("select at, role, phase, text from turns where session=? order by id", (sid,)).fetchall()
    return [{"at": r["at"], "role": r["role"], "phase": r["phase"], "text": unseal(r["text"])} for r in rows]


def save_summary(sid: str, data: dict) -> None:
    with connect() as db:
        db.execute("insert into summaries(session, payload) values(?,?) on conflict(session) do update set payload=excluded.payload", (sid, seal(data)))


def summary(sid: str) -> dict | None:
    with connect() as db:
        row = db.execute("select payload from summaries where session=?", (sid,)).fetchone()
    return unseal(row["payload"]) if row else None


def plan(slug: str) -> dict:
    with connect() as db:
        row = db.execute("select * from plan where slug=?", (slug,)).fetchone()
    return dict(row) if row else {"slug": slug, "stage": "assessment", "next_at": None, "concluded": 0}


def save_plan(slug: str, stage: str, next_at: float | None, concluded: bool) -> None:
    with connect() as db:
        db.execute("insert into plan(slug, stage, next_at, concluded) values(?,?,?,?) on conflict(slug) do update set "
                   "stage=excluded.stage, next_at=excluded.next_at, concluded=excluded.concluded", (slug, stage, next_at, int(concluded)))


def erase(slug: str) -> None:
    _last_reading.pop(slug, None)
    _consent.pop(slug, None)
    with connect() as db:
        db.execute("delete from sessions where slug=?", (slug,))
        for table in ("consent", "baseline", "readings", "plan"):
            db.execute(f"delete from {table} where slug=?", (slug,))
    with connect() as db:
        db.execute("pragma wal_checkpoint(truncate)")
