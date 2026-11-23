import logging
import threading
import time

import native_core
from config import STATE_DIR

from agenti.nodes.peer_identity import identity

log = logging.getLogger("nuxiva.peer")

LEDGER_FILE = STATE_DIR / "peer_ledger.chain"
MAX_WIRE = 65536


class PeerLedgerService:
    def __init__(self, path=LEDGER_FILE, clock=time.time) -> None:
        self._path = path
        self._clock = clock
        self._lock = threading.Lock()
        self._inner = None
        self._started = False

    def _now(self) -> int:
        return int(self._clock() * 1000)

    def _open(self):
        if self._started:
            return self._inner
        self._started = True
        cls = native_core.symbol("PeerLedger")
        if cls is None:
            log.warning("Registro indirizzi non disponibile: modulo Rust assente")
            return None
        inner = cls(identity().seed_hex())
        try:
            if self._path.exists():
                inner.load(str(self._path), self._now())
        except (OSError, ValueError) as exc:
            log.error("Registro indirizzi illeggibile, riparto da zero: %s", exc)
        self._inner = inner
        return inner

    @property
    def available(self) -> bool:
        with self._lock:
            return self._open() is not None

    def enroll(self, peer_id: str) -> bool:
        with self._lock:
            inner = self._open()
            if inner is None:
                return False
            try:
                inner.enroll(peer_id)
            except ValueError:
                return False
            return True

    def announce(self, addrs: list[str]) -> bool:
        with self._lock:
            inner = self._open()
            if inner is None:
                return False
            try:
                changed = bool(inner.announce(addrs, self._now()))
                if changed:
                    inner.save(str(self._path))
            except (OSError, ValueError) as exc:
                log.warning("Registro indirizzi non aggiornato: %s", exc)
                return False
            return changed

    def candidates(self, peer_id: str) -> list[str]:
        with self._lock:
            inner = self._open()
            return list(inner.candidates(peer_id)) if inner is not None else []

    def handle(self, wire: str) -> str | None:
        if not isinstance(wire, str) or len(wire) > MAX_WIRE:
            return None
        with self._lock:
            inner = self._open()
            if inner is None:
                return None
            try:
                reply = inner.handle(wire, self._now())
                return reply
            except ValueError:
                return None

    def digest(self) -> str | None:
        with self._lock:
            inner = self._open()
            if inner is None:
                return None
            try:
                return inner.digest_request()
            except ValueError:
                return None


ledger = PeerLedgerService()
