import json
import logging
import socket
import threading
import time

from connection import peer_envelope

log = logging.getLogger("nuxiva.peer")

PEER_PORT = 50507
MAX_DATAGRAM = 1200
CLOCK_SKEW_MS = 60_000
RATE_PER_WINDOW = 8
RATE_WINDOW = 1.0
MAX_SOURCES = 1024


class Throttle:
    def __init__(self, per_window: int = RATE_PER_WINDOW, window: float = RATE_WINDOW, clock=time.monotonic) -> None:
        self.per_window, self.window, self.clock = per_window, window, clock
        self.seen: dict[str, tuple[float, int]] = {}

    def allow(self, source: str) -> bool:
        now = self.clock()
        if len(self.seen) >= MAX_SOURCES and source not in self.seen:
            self.seen = {k: v for k, v in self.seen.items() if now - v[0] < self.window}
            if len(self.seen) >= MAX_SOURCES:
                return False
        start, count = self.seen.get(source, (now, 0))
        if now - start >= self.window:
            start, count = now, 0
        self.seen[source] = (start, count + 1)
        return count + 1 <= self.per_window


class Tracker:
    def __init__(self, server_id: str, clock=time.time) -> None:
        self.trusted = {server_id}
        self.clock = clock
        self.last_seq = -1

    def accept(self, raw: bytes) -> list[str] | None:
        if len(raw) > MAX_DATAGRAM:
            return None
        try:
            envelope = json.loads(raw.decode("utf-8"))
            addrs = peer_envelope.verify_locate(envelope, self.trusted)
        except (ValueError, UnicodeDecodeError):
            return None
        if abs(int(self.clock() * 1000) - envelope["ts"]) > CLOCK_SKEW_MS or envelope["seq"] <= self.last_seq:
            return None
        self.last_seq = envelope["seq"]
        return addrs


class PeerListener(threading.Thread):
    def __init__(self, server_id: str, on_locate, port: int = PEER_PORT, bind: str = "") -> None:
        super().__init__(daemon=True, name="peer")
        self.tracker, self.on_locate = Tracker(server_id), on_locate
        self.throttle = Throttle()
        self.port, self.bind = port, bind
        self.stop_flag = threading.Event()
        self.bound = threading.Event()

    def stop(self) -> None:
        self.stop_flag.set()

    def _socket(self) -> socket.socket:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind((self.bind, self.port))
        sock.settimeout(1.0)
        return sock

    def handle(self, raw: bytes, source: str) -> None:
        if not self.throttle.allow(source):
            return
        addrs = self.tracker.accept(raw)
        if addrs:
            self.on_locate(addrs)

    def run(self) -> None:
        try:
            sock = self._socket()
        except OSError as exc:
            log.warning("Ascolto degli indirizzi del server non disponibile: %s", exc)
            return
        self.port = sock.getsockname()[1]
        self.bound.set()
        with sock:
            while not self.stop_flag.is_set():
                try:
                    raw, source = sock.recvfrom(MAX_DATAGRAM + 1)
                except TimeoutError:
                    continue
                except OSError as exc:
                    log.warning("Ascolto degli indirizzi interrotto: %s", exc)
                    return
                self.handle(raw, source[0])
