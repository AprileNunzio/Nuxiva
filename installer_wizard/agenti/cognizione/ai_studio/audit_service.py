"""Registro di audit a catena di hash (append-only, verificabile).

Ogni voce include l'hash della precedente: qualsiasi modifica o cancellazione
retroattiva rompe la catena e viene segnalata da ``verify()``.
"""

import hashlib
import json
import time
from typing import Any, Dict, List

from .store import StudioStore

GENESIS = "0" * 64
MAX_DETAIL_CHARS = 2000


def _digest(prev_hash: str, ts: int, actor: str, action: str, detail: str) -> str:
    payload = json.dumps([prev_hash, ts, actor, action, detail], ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class AuditService:
    def __init__(self, store: StudioStore) -> None:
        self.store = store
        with self.store._lock, self.store._get_connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS audit_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts INTEGER NOT NULL,
                    actor TEXT NOT NULL,
                    action TEXT NOT NULL,
                    detail TEXT NOT NULL DEFAULT '',
                    prev_hash TEXT NOT NULL,
                    hash TEXT NOT NULL
                )
                """
            )

    def append(self, actor: str, action: str, detail: str = "") -> Dict[str, Any]:
        detail = detail[:MAX_DETAIL_CHARS]
        ts = int(time.time())
        with self.store._lock, self.store._get_connection() as conn:
            row = conn.execute("SELECT hash FROM audit_log ORDER BY id DESC LIMIT 1").fetchone()
            prev = row["hash"] if row else GENESIS
            h = _digest(prev, ts, actor, action, detail)
            cur = conn.execute(
                "INSERT INTO audit_log (ts, actor, action, detail, prev_hash, hash) VALUES (?,?,?,?,?,?)",
                (ts, actor, action, detail, prev, h),
            )
            return {"id": cur.lastrowid, "ts": ts, "actor": actor, "action": action, "detail": detail, "hash": h}

    def list(self, limit: int = 100, action_prefix: str = "") -> List[Dict[str, Any]]:
        limit = max(1, min(limit, 500))
        sql = "SELECT * FROM audit_log"
        args: List[Any] = []
        if action_prefix:
            sql += " WHERE action LIKE ?"
            args.append(action_prefix.replace("%", "").replace("_", "") + "%")
        sql += " ORDER BY id DESC LIMIT ?"
        args.append(limit)
        with self.store._lock, self.store._get_connection() as conn:
            return [dict(r) for r in conn.execute(sql, args).fetchall()]

    def verify(self) -> Dict[str, Any]:
        with self.store._lock, self.store._get_connection() as conn:
            rows = conn.execute("SELECT * FROM audit_log ORDER BY id ASC").fetchall()
        prev = GENESIS
        for r in rows:
            expected = _digest(prev, r["ts"], r["actor"], r["action"], r["detail"])
            if r["prev_hash"] != prev or r["hash"] != expected:
                return {"ok": False, "entries": len(rows), "broken_at": r["id"]}
            prev = r["hash"]
        return {"ok": True, "entries": len(rows), "broken_at": None}
