import io
import os
import re
import secrets
import sqlite3
import threading
import time
import wave
from contextlib import closing
from pathlib import Path

import numpy as np
from cryptography.fernet import Fernet

from sealed import write_private

RATE = 16000
KINDS = ("command", "heard", "wake")
VERDICTS = ("", "ok", "wrong")
SLUG = re.compile(r"^[a-z0-9][a-z0-9-]{0,40}$")
ID = re.compile(r"^[0-9a-f]{12}$")
TEXT_MAX = 2000
NOTE_MAX = 600
PAGE_MAX = 200
SCHEMA = """
CREATE TABLE IF NOT EXISTS entries (
    id TEXT PRIMARY KEY, ts REAL NOT NULL, kind TEXT NOT NULL, lang TEXT NOT NULL DEFAULT '',
    speaker TEXT NOT NULL DEFAULT '', score REAL NOT NULL DEFAULT 0, woke INTEGER NOT NULL DEFAULT 0,
    ms INTEGER NOT NULL DEFAULT 0, live INTEGER NOT NULL DEFAULT 0, dur REAL NOT NULL DEFAULT 0,
    text BLOB NOT NULL, audio INTEGER NOT NULL DEFAULT 0, verdict TEXT NOT NULL DEFAULT '',
    correction BLOB, fix_speaker TEXT NOT NULL DEFAULT '', note BLOB, reviewed_at REAL NOT NULL DEFAULT 0,
    applied INTEGER NOT NULL DEFAULT 0)
"""


def default_root() -> Path:
    return Path(os.environ.get("NUXIVA_EAR_REVIEW_DIR", "/var/lib/nuxiva/ear_review")) / "journal"


def wav_bytes(audio: np.ndarray) -> bytes:
    pcm = (np.clip(audio, -1, 1) * 32767).astype("<i2").tobytes()
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(RATE)
        handle.writeframes(pcm)
    return buffer.getvalue()


def samples(wav: bytes) -> np.ndarray:
    with wave.open(io.BytesIO(wav), "rb") as handle:
        raw = handle.readframes(handle.getnframes())
    return np.frombuffer(raw, dtype="<i2").astype(np.float32) / 32768.0


class Journal:

    def __init__(self, root: Path | None = None) -> None:
        self.root = root or default_root()
        self.lock = threading.Lock()
        self.ready = False
        self.fernet: Fernet | None = None

    @property
    def db_path(self) -> Path:
        return self.root / "journal.db"

    def _ensure(self) -> None:
        if not self.ready:
            self.root.mkdir(parents=True, exist_ok=True)
            os.chmod(self.root, 0o700)
            key = self.root / "journal.key"
            if not key.exists():
                write_private(key, Fernet.generate_key())
            self.fernet = Fernet(key.read_bytes())
            with closing(sqlite3.connect(self.db_path)) as conn:
                conn.execute("PRAGMA journal_mode=WAL")
                conn.execute(SCHEMA)
                conn.execute("CREATE INDEX IF NOT EXISTS entries_ts ON entries(ts)")
                conn.commit()
            os.chmod(self.db_path, 0o600)
            self.ready = True

    def _open(self) -> sqlite3.Connection:
        self._ensure()
        conn = sqlite3.connect(self.db_path, timeout=10)
        conn.row_factory = sqlite3.Row
        return conn

    def _seal(self, text: str, limit: int) -> bytes:
        return self.fernet.encrypt(text[:limit].encode())

    def _open_text(self, blob: bytes | None) -> str:
        return self.fernet.decrypt(blob).decode() if blob else ""

    def _clip(self, entry_id: str) -> Path:
        return self.root / f"{entry_id}.clip"

    def record(self, kind: str, text: str, lang: str = "", speaker: str | None = None, score: float = 0.0,
               woke: bool = False, ms: int = 0, live: bool = False, audio: np.ndarray | None = None) -> str:
        if kind not in KINDS or not text.strip():
            return ""
        entry_id = secrets.token_hex(6)
        who = speaker if speaker and SLUG.match(speaker) else ""
        with self.lock, closing(self._open()) as conn:
            keep = audio is not None and len(audio) > 0
            if keep:
                write_private(self._clip(entry_id), self.fernet.encrypt(wav_bytes(audio)))
            conn.execute(
                "INSERT INTO entries (id, ts, kind, lang, speaker, score, woke, ms, live, dur, text, audio) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                (entry_id, time.time(), kind, lang[:8], who, float(score), int(woke), int(ms), int(live),
                 round(len(audio) / RATE, 2) if keep else 0.0, self._seal(text.strip(), TEXT_MAX), int(keep)))
            conn.commit()
        return entry_id

    def _row(self, row: sqlite3.Row) -> dict:
        return {"id": row["id"], "ts": row["ts"], "kind": row["kind"], "lang": row["lang"], "speaker": row["speaker"],
                "score": row["score"], "woke": bool(row["woke"]), "ms": row["ms"], "live": bool(row["live"]),
                "dur": row["dur"], "text": self._open_text(row["text"]), "audio": bool(row["audio"]),
                "verdict": row["verdict"], "correction": self._open_text(row["correction"]),
                "fix_speaker": row["fix_speaker"], "note": self._open_text(row["note"]),
                "reviewed_at": row["reviewed_at"], "applied": bool(row["applied"])}

    def entries(self, limit: int = 50, before: float = 0.0, kind: str = "", speaker: str = "",
             verdict: str = "", query: str = "") -> list[dict]:
        clauses, args = [], []
        if before > 0:
            clauses.append("ts < ?")
            args.append(before)
        if kind in KINDS:
            clauses.append("kind = ?")
            args.append(kind)
        if speaker == "-":
            clauses.append("speaker = ''")
        elif speaker and SLUG.match(speaker):
            clauses.append("speaker = ?")
            args.append(speaker)
        if verdict == "pending":
            clauses.append("verdict = ''")
        elif verdict in ("ok", "wrong"):
            clauses.append("verdict = ?")
            args.append(verdict)
        where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
        with self.lock, closing(self._open()) as conn:
            rows = conn.execute(f"SELECT * FROM entries {where} ORDER BY ts DESC LIMIT ?",
                                (*args, max(1, min(PAGE_MAX, limit)) if not query else 2000)).fetchall()
        items = [self._row(row) for row in rows]
        needle = query.strip().lower()
        if needle:
            items = [i for i in items if needle in i["text"].lower() or needle in i["correction"].lower()]
        return items[:max(1, min(PAGE_MAX, limit))]

    def get(self, entry_id: str) -> dict | None:
        if not ID.match(entry_id):
            return None
        with self.lock, closing(self._open()) as conn:
            row = conn.execute("SELECT * FROM entries WHERE id = ?", (entry_id,)).fetchone()
        return self._row(row) if row else None

    def audio(self, entry_id: str) -> bytes | None:
        if not ID.match(entry_id):
            return None
        with self.lock:
            self._ensure()
            try:
                return self.fernet.decrypt(self._clip(entry_id).read_bytes())
            except FileNotFoundError:
                return None

    def feedback(self, entry_id: str, verdict: str, correction: str = "", speaker: str = "", note: str = "") -> bool:
        if verdict not in VERDICTS or not ID.match(entry_id):
            return False
        who = speaker if speaker and SLUG.match(speaker) else ""
        with self.lock, closing(self._open()) as conn:
            cur = conn.execute(
                "UPDATE entries SET verdict=?, correction=?, fix_speaker=?, note=?, reviewed_at=?, applied=0 WHERE id=?",
                (verdict, self._seal(correction.strip(), TEXT_MAX) if correction.strip() else None, who,
                 self._seal(note.strip(), NOTE_MAX) if note.strip() else None, time.time() if verdict else 0.0, entry_id))
            conn.commit()
        return cur.rowcount == 1

    def pending(self, limit: int = 20) -> list[dict]:
        with self.lock, closing(self._open()) as conn:
            rows = conn.execute("SELECT * FROM entries WHERE verdict != '' AND applied = 0 ORDER BY reviewed_at LIMIT ?",
                                (limit,)).fetchall()
        return [self._row(row) for row in rows]

    def mark_applied(self, entry_id: str) -> None:
        with self.lock, closing(self._open()) as conn:
            conn.execute("UPDATE entries SET applied = 1 WHERE id = ?", (entry_id,))
            conn.commit()

    def _drop(self, conn: sqlite3.Connection, ids: list[str]) -> None:
        for entry_id in ids:
            self._clip(entry_id).unlink(missing_ok=True)
            conn.execute("DELETE FROM entries WHERE id = ?", (entry_id,))
        conn.commit()

    def delete(self, entry_id: str) -> bool:
        if not ID.match(entry_id):
            return False
        with self.lock, closing(self._open()) as conn:
            exists = conn.execute("SELECT 1 FROM entries WHERE id = ?", (entry_id,)).fetchone()
            self._drop(conn, [entry_id])
        return bool(exists)

    def purge(self) -> int:
        with self.lock, closing(self._open()) as conn:
            ids = [row["id"] for row in conn.execute("SELECT id FROM entries")]
            self._drop(conn, ids)
        for stray in self.root.glob("*.clip"):
            stray.unlink(missing_ok=True)
        return len(ids)

    def prune(self, days: float, audio_days: float, cap_mb: float) -> int:
        now = time.time()
        removed = 0
        with self.lock, closing(self._open()) as conn:
            stale = [r["id"] for r in conn.execute(
                "SELECT id FROM entries WHERE ts < ? AND NOT (verdict != '' AND applied = 0)", (now - days * 86400,))]
            self._drop(conn, stale)
            removed += len(stale)
            old_audio = [r["id"] for r in conn.execute(
                "SELECT id FROM entries WHERE audio = 1 AND ts < ? AND NOT (verdict != '' AND applied = 0)",
                (now - audio_days * 86400,))]
            for entry_id in old_audio:
                self._clip(entry_id).unlink(missing_ok=True)
                conn.execute("UPDATE entries SET audio = 0 WHERE id = ?", (entry_id,))
            conn.commit()
            total = sum(p.stat().st_size for p in self.root.glob("*.clip"))
            oldest = [r["id"] for r in conn.execute("SELECT id FROM entries WHERE audio = 1 ORDER BY ts")]
            for entry_id in oldest:
                if total <= cap_mb * 1024 * 1024:
                    break
                path = self._clip(entry_id)
                total -= path.stat().st_size if path.exists() else 0
                path.unlink(missing_ok=True)
                conn.execute("UPDATE entries SET audio = 0 WHERE id = ?", (entry_id,))
            conn.commit()
        return removed

    def stats(self) -> dict:
        with self.lock, closing(self._open()) as conn:
            total = conn.execute("SELECT COUNT(*) FROM entries").fetchone()[0]
            by = {r["verdict"] or "pending": r["n"] for r in conn.execute(
                "SELECT verdict, COUNT(*) AS n FROM entries GROUP BY verdict")}
            speakers = {r["speaker"] or "-": r["n"] for r in conn.execute(
                "SELECT speaker, COUNT(*) AS n FROM entries GROUP BY speaker")}
        size = sum(p.stat().st_size for p in self.root.glob("*.clip"))
        return {"total": total, "pending": by.get("pending", 0), "ok": by.get("ok", 0), "wrong": by.get("wrong", 0),
                "speakers": speakers, "audio_mb": round(size / 1048576, 1)}


journal = Journal()
