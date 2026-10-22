import logging
import sqlite3
import threading
import time
from contextlib import closing
from pathlib import Path
from typing import Optional

from server.core.core_platform.errors import CortexFailure, fail
from server.core.core_platform.result import Ok, Result
from server.core.core_platform.zero_trust_crypto import ZeroTrustVault

logger = logging.getLogger("nuxiva.plasticity.ledger")

SEAL_PURPOSE = "plasticity-example"
ASSOCIATED = b"nuxiva.cortex.plasticity.v1"
SCHEMA = (
    "CREATE TABLE IF NOT EXISTS usage (neuron_id TEXT PRIMARY KEY, first_seen REAL NOT NULL, last_used REAL NOT NULL,"
    " successes INTEGER NOT NULL DEFAULT 0, failures INTEGER NOT NULL DEFAULT 0)",
    "CREATE TABLE IF NOT EXISTS examples (id INTEGER PRIMARY KEY AUTOINCREMENT, neuron_id TEXT NOT NULL,"
    " sealed BLOB NOT NULL, at REAL NOT NULL)",
    "CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value REAL NOT NULL)",
    "CREATE INDEX IF NOT EXISTS examples_neuron ON examples (neuron_id)",
)
MAX_EXAMPLES_PER_NEURON = 500


class PlasticityLedger:
    def __init__(self, path: Path, vault: ZeroTrustVault) -> None:
        self._path = path
        self._vault = vault
        self._lock = threading.Lock()
        self._ready = False

    def _connect(self) -> sqlite3.Connection:
        if not self._ready:
            self._path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        connection = sqlite3.connect(self._path, timeout=10)
        if not self._ready:
            for statement in SCHEMA:
                connection.execute(statement)
            connection.commit()
            self._ready = True
        return connection

    def _run(self, action) -> Result[object, CortexFailure]:
        with self._lock:
            try:
                with closing(self._connect()) as connection:
                    value = action(connection)
                    connection.commit()
                    return Ok(value)
            except sqlite3.Error as exc:
                logger.error("Plasticity ledger failure (%s)", type(exc).__name__)
                return fail("platform.storage.io_failed")

    def touch(self, neuron_id: str, success: Optional[bool], now: Optional[float] = None) -> Result[object, CortexFailure]:
        moment = time.time() if now is None else now
        wins, losses = (1, 0) if success is True else (0, 1) if success is False else (0, 0)

        def action(connection: sqlite3.Connection) -> None:
            connection.execute(
                "INSERT INTO usage (neuron_id, first_seen, last_used, successes, failures) VALUES (?, ?, ?, ?, ?)"
                " ON CONFLICT(neuron_id) DO UPDATE SET last_used = excluded.last_used,"
                " successes = successes + ?, failures = failures + ?",
                (neuron_id, moment, moment, wins, losses, wins, losses))

        return self._run(action)

    def idle_days(self, neuron_id: str, now: float) -> Result[object, CortexFailure]:
        def action(connection: sqlite3.Connection) -> float:
            row = connection.execute("SELECT last_used FROM usage WHERE neuron_id = ?", (neuron_id,)).fetchone()
            if row is None:
                connection.execute("INSERT INTO usage (neuron_id, first_seen, last_used) VALUES (?, ?, ?)",
                                   (neuron_id, now, now))
                return 0.0
            return max(0.0, (now - row[0]) / 86_400.0)

        return self._run(action)

    def forget(self, neuron_id: str) -> Result[object, CortexFailure]:
        def action(connection: sqlite3.Connection) -> None:
            connection.execute("DELETE FROM usage WHERE neuron_id = ?", (neuron_id,))
            connection.execute("DELETE FROM examples WHERE neuron_id = ?", (neuron_id,))

        return self._run(action)

    def add_example(self, neuron_id: str, utterance: str, now: Optional[float] = None) -> Result[object, CortexFailure]:
        sealed = self._vault.seal_bytes(SEAL_PURPOSE, utterance.encode("utf-8"), ASSOCIATED)
        if not sealed.is_ok:
            return sealed
        moment = time.time() if now is None else now

        def action(connection: sqlite3.Connection) -> None:
            connection.execute("INSERT INTO examples (neuron_id, sealed, at) VALUES (?, ?, ?)",
                               (neuron_id, sealed.value, moment))
            connection.execute(
                "DELETE FROM examples WHERE neuron_id = ? AND id NOT IN"
                " (SELECT id FROM examples WHERE neuron_id = ? ORDER BY id DESC LIMIT ?)",
                (neuron_id, neuron_id, MAX_EXAMPLES_PER_NEURON))

        return self._run(action)

    def examples(self) -> Result[list[tuple[str, str]], CortexFailure]:
        rows = self._run(lambda c: c.execute("SELECT neuron_id, sealed FROM examples ORDER BY id").fetchall())
        if not rows.is_ok:
            return rows
        out = []
        for neuron_id, sealed in rows.value:
            opened = self._vault.open_bytes(SEAL_PURPOSE, sealed, ASSOCIATED)
            if opened.is_ok:
                out.append((neuron_id, opened.value.decode("utf-8")))
            else:
                logger.warning("Skipping an unreadable plasticity example (%s)", opened.error.code)
        return Ok(out)

    def last_run(self) -> Result[object, CortexFailure]:
        def action(connection: sqlite3.Connection) -> Optional[float]:
            row = connection.execute("SELECT value FROM meta WHERE key = 'last_consolidation'").fetchone()
            return None if row is None else row[0]

        return self._run(action)

    def mark_run(self, moment: float) -> Result[object, CortexFailure]:
        return self._run(lambda c: c.execute(
            "INSERT INTO meta (key, value) VALUES ('last_consolidation', ?)"
            " ON CONFLICT(key) DO UPDATE SET value = excluded.value", (moment,)))

    def totals(self) -> Result[object, CortexFailure]:
        def action(connection: sqlite3.Connection) -> dict:
            usage = connection.execute("SELECT COUNT(*), COALESCE(SUM(successes),0), COALESCE(SUM(failures),0) FROM usage").fetchone()
            examples = connection.execute("SELECT COUNT(*) FROM examples").fetchone()
            return {"neurons": usage[0], "successes": usage[1], "failures": usage[2], "examples": examples[0]}

        return self._run(action)
