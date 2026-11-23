import logging
import secrets
import threading
import time

from connection import ledger
from connection.client import ServerError, Unreachable

log = logging.getLogger("nuxiva.peer")

SYNC_EVERY = 60.0


class LedgerWatch(threading.Thread):
    def __init__(self, client, server_id: str, path, is_online, offer, clock=time.time, wait=None) -> None:
        super().__init__(daemon=True, name="ledger")
        self.client, self.server_id, self.path = client, server_id, path
        self.is_online, self.offer, self.clock = is_online, offer, clock
        self.stop_flag = threading.Event()
        self.wait = wait or self.stop_flag.wait
        self.attempt = 0
        self.book = self._open()

    def _now(self) -> int:
        return int(self.clock() * 1000)

    def _open(self) -> ledger.Ledger:
        try:
            return ledger.load({self.server_id}, self.path, self._now())
        except ledger.LedgerError as exc:
            log.warning("Registro indirizzi non leggibile, riparto da zero: %s", exc.code)
            return ledger.Ledger({self.server_id})

    def stop(self) -> None:
        self.stop_flag.set()

    def sync(self) -> int:
        request = ledger.encode(self.book.digest_request()).decode("ascii")
        reply = self.client.request("/api/nodes/peer/sync", {"wire": request}, timeout=10)
        raw = reply.get("wire") if isinstance(reply, dict) else None
        if not isinstance(raw, str):
            return 0
        report = self.book.absorb(ledger.decode(raw.encode("utf-8")), self._now())
        if report["applied"]:
            ledger.save(self.book, self.path)
        return report["applied"]

    def recover(self) -> bool:
        addrs = self.book.candidates(self.server_id)
        return bool(addrs) and self.offer(addrs)

    def step(self) -> float:
        if self.is_online():
            self.attempt = 0
            try:
                self.sync()
            except (ServerError, Unreachable, ledger.LedgerError, OSError) as exc:
                log.debug("Registro indirizzi non sincronizzato: %s", exc)
            return SYNC_EVERY
        if self.recover():
            self.attempt = 0
            return 1.0
        delay = ledger.reconnect_delay_ms(self.attempt, secrets.randbits(32)) / 1000.0
        self.attempt = min(self.attempt + 1, 16)
        return delay

    def run(self) -> None:
        while not self.stop_flag.is_set():
            try:
                delay = self.step()
            except Exception:
                log.exception("Ciclo del registro indirizzi interrotto")
                delay = SYNC_EVERY
            if self.wait(delay):
                return
