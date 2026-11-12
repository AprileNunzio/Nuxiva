import logging
import sqlite3
import threading
from contextlib import closing
from pathlib import Path
from typing import Any, Callable, Sequence

from server.core.core_platform.errors import CortexFailure, fail
from server.core.core_platform.result import Ok, Result
from server.core.core_platform.zero_trust_crypto import ZeroTrustVault


class SealedSqlite:
    def __init__(self, path: Path, vault: ZeroTrustVault, schema: Sequence[str], log: logging.Logger) -> None:
        self._path = path
        self._vault = vault
        self._schema = tuple(schema)
        self._log = log
        self._lock = threading.Lock()
        self._ready = False

    def _connect(self) -> sqlite3.Connection:
        if not self._ready:
            self._path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        connection = sqlite3.connect(self._path, timeout=10)
        if not self._ready:
            for statement in self._schema:
                connection.execute(statement)
            connection.commit()
            self._ready = True
        return connection

    def _run(self, action: Callable[[sqlite3.Connection], Any]) -> Result[Any, CortexFailure]:
        with self._lock:
            try:
                with closing(self._connect()) as connection:
                    value = action(connection)
                    connection.commit()
                    return Ok(value)
            except sqlite3.Error as exc:
                self._log.error("Storage failure (%s)", type(exc).__name__)
                return fail("platform.storage.io_failed")
