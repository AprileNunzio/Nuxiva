import logging
import time
from pathlib import Path
from typing import Optional

from server.core.core_platform.errors import CortexFailure
from server.core.core_platform.result import Ok, Result
from server.core.core_platform.sealed_sqlite import SealedSqlite
from server.core.core_platform.zero_trust_crypto import ZeroTrustVault

logger = logging.getLogger("nuxiva.skill_forge.misses")

SEAL_PURPOSE = "forge-miss"
ASSOCIATED = b"nuxiva.cortex.forge.misses.v1"
MAX_MISSES = 3_000
MAX_CHARS = 300
SCHEMA = (
    "CREATE TABLE IF NOT EXISTS misses (id INTEGER PRIMARY KEY AUTOINCREMENT, sealed BLOB NOT NULL, at REAL NOT NULL)",
    "CREATE TABLE IF NOT EXISTS attempts (key TEXT PRIMARY KEY, at REAL NOT NULL, outcome TEXT NOT NULL)",
)


class MissLedger(SealedSqlite):
    def __init__(self, path: Path, vault: ZeroTrustVault) -> None:
        super().__init__(path, vault, SCHEMA, logger)

    def note(self, utterance: str, now: Optional[float] = None) -> Result[None, CortexFailure]:
        text = utterance.strip()[:MAX_CHARS]
        if not text:
            return Ok(None)
        sealed = self._vault.seal_bytes(SEAL_PURPOSE, text.encode("utf-8"), ASSOCIATED)
        if not sealed.is_ok:
            return sealed
        moment = time.time() if now is None else now

        def action(connection):
            connection.execute("INSERT INTO misses (sealed, at) VALUES (?, ?)", (sealed.value, moment))
            connection.execute("DELETE FROM misses WHERE id NOT IN (SELECT id FROM misses ORDER BY id DESC LIMIT ?)", (MAX_MISSES,))

        return self._run(action)

    def recent(self) -> Result[list[str], CortexFailure]:
        rows = self._run(lambda c: c.execute("SELECT sealed FROM misses ORDER BY id").fetchall())
        if not rows.is_ok:
            return rows
        out = []
        for (sealed,) in rows.value:
            opened = self._vault.open_bytes(SEAL_PURPOSE, sealed, ASSOCIATED)
            if opened.is_ok:
                out.append(opened.value.decode("utf-8"))
            else:
                logger.warning("Skipping an unreadable miss (%s)", opened.error.code)
        return Ok(out)

    def count(self) -> Result[int, CortexFailure]:
        return self._run(lambda c: c.execute("SELECT COUNT(*) FROM misses").fetchone()[0])

    def expire(self, days: float, now: Optional[float] = None) -> Result[dict, CortexFailure]:
        moment = time.time() if now is None else now
        removed = self._run(lambda c: c.execute("DELETE FROM misses WHERE at < ?", (moment - days * 86_400.0,)).rowcount)
        return removed if not removed.is_ok else Ok({"expired": removed.value})

    def clear(self) -> Result[None, CortexFailure]:
        return self._run(lambda c: c.execute("DELETE FROM misses"))

    def settled(self, texts: list[str]) -> Result[int, CortexFailure]:
        wanted = set(texts)
        stored = self._run(lambda c: c.execute("SELECT id, sealed FROM misses").fetchall())
        if not stored.is_ok:
            return stored
        doomed = []
        for row_id, sealed in stored.value:
            opened = self._vault.open_bytes(SEAL_PURPOSE, sealed, ASSOCIATED)
            if opened.is_ok and opened.value.decode("utf-8") in wanted:
                doomed.append((row_id,))
        removed = self._run(lambda c: c.executemany("DELETE FROM misses WHERE id = ?", doomed))
        return removed if not removed.is_ok else Ok(len(doomed))

    def tried_recently(self, key: str, days: float, now: Optional[float] = None) -> Result[bool, CortexFailure]:
        moment = time.time() if now is None else now

        def action(connection):
            row = connection.execute("SELECT at FROM attempts WHERE key = ?", (key,)).fetchone()
            return row is not None and (moment - row[0]) < days * 86_400.0

        return self._run(action)

    def record_attempt(self, key: str, outcome: str, now: Optional[float] = None) -> Result[None, CortexFailure]:
        moment = time.time() if now is None else now
        return self._run(lambda c: c.execute(
            "INSERT INTO attempts (key, at, outcome) VALUES (?, ?, ?)"
            " ON CONFLICT(key) DO UPDATE SET at = excluded.at, outcome = excluded.outcome", (key, moment, outcome)))

    def attempts(self) -> Result[list[dict], CortexFailure]:
        rows = self._run(lambda c: c.execute("SELECT key, at, outcome FROM attempts ORDER BY at DESC LIMIT 50").fetchall())
        return rows if not rows.is_ok else Ok([{"key": k, "at": a, "outcome": o} for k, a, o in rows.value])
