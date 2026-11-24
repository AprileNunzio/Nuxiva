import itertools
import logging
import os
import socket
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from screenshot import capture, rules, sink
from screenshot.sink import AuthError
from screenshot.credentials import CredentialError
from screenshot.spool import Spool

log = logging.getLogger("nuxiva.screenshot")
DEBOUNCE = 1.5
FLUSH_EVERY = 5
PRUNE_EVERY = 3600
QUIET = frozenset({"ok"})


@dataclass(frozen=True)
class Outcome:
    status: str
    key: str
    tone: str
    values: dict = field(default_factory=dict)


class Service:
    def __init__(self, spool_dir: Path, notify, text, guest_flag: Path | None = None, hotkey_factory=None,
                 vault=None, connect=None, clipboard=None) -> None:
        self.config = rules.Config()
        self.spool = Spool(spool_dir)
        self.notify, self.text = notify, text
        self.guest_flag = guest_flag or Path(os.environ.get("ProgramData", ".")) / "Nuxiva" / "guests-present"
        self.vault, self.connect, self.clipboard = vault, connect, clipboard
        self.counter = itertools.count()
        self.last = 0.0
        self.lock = threading.Lock()
        self.stop_event = threading.Event()
        self.hotkey = None
        self.hotkey_factory = hotkey_factory
        self.worker: threading.Thread | None = None
        self.connected = False
        self.auth_warned = False

    def apply(self, settings: dict, auth=None) -> None:
        if self.vault is not None and auth is not None:
            try:
                if self.vault.update(auth):
                    self.connected, self.auth_warned = False, False
            except (CredentialError, OSError) as exc:
                log.warning("Credenziali SMB degli screenshot non valide o non cifrabili: %s", type(exc).__name__)
        config = rules.from_settings(settings)
        if config == self.config:
            return
        self.config = config
        self.connected, self.auth_warned = False, False
        if config.enabled and self.hotkey is None and self.hotkey_factory:
            self.hotkey = self.hotkey_factory(self.trigger)
            if not self.hotkey.start():
                log.warning("Tasto Stamp non intercettabile su questo PC")
                self.say(Outcome("hotkey", "screenshot.hotkey_unavailable", "error"))
        if not config.enabled and self.hotkey is not None:
            self.hotkey.stop()
            self.hotkey = None

    def guests(self) -> bool:
        try:
            return self.guest_flag.read_text(encoding="ascii", errors="ignore").strip() in ("1", "true", "yes")
        except FileNotFoundError:
            return False
        except OSError as exc:
            log.warning("Stato ospiti illeggibile, considero ospiti presenti: %s", exc)
            return True

    def denied(self, locked: bool) -> Outcome | None:
        if not self.config.enabled:
            return Outcome("disabled", "screenshot.disabled", "warn")
        if not self.config.active:
            return Outcome("no_target", "screenshot.no_target", "warn")
        if self.config.block_locked and locked:
            return Outcome("locked", "screenshot.blocked", "warn")
        if self.config.block_guests and self.guests():
            return Outcome("guests", "screenshot.blocked", "warn")
        return None

    def trigger(self) -> None:
        now = time.monotonic()
        if now - self.last < DEBOUNCE:
            return
        self.last = now
        threading.Thread(target=self.capture_once, daemon=True, name="screenshot").start()

    def message(self, outcome: Outcome) -> str:
        return self.text(outcome.key, **outcome.values)

    def say(self, outcome: Outcome) -> None:
        if outcome.tone in QUIET and not self.config.notice:
            return
        self.notify(self.message(outcome), outcome.tone)

    def capture_once(self, locked: bool | None = None) -> str:
        outcome = self.shoot(locked)
        self.say(outcome)
        return outcome.status

    def shoot(self, locked: bool | None = None) -> Outcome:
        with self.lock:
            blocked = self.denied(capture.locked() if locked is None else locked)
            if blocked:
                return blocked
            try:
                image = capture.grab()
                capture.apply_masks(image, self.config.masks)
                self._to_clipboard(image)
                data = capture.png(image)
                name = rules.file_name(socket.gethostname(), datetime.now().astimezone(), next(self.counter))
                self.spool.enqueue(name, data)
            except (capture.CaptureError, sink.SinkError, OSError) as exc:
                log.warning("Screenshot non riuscito: %s", exc)
                return Outcome("failed", "screenshot.failed", "error", {"reason": str(exc)[:120]})
            self.spool.next_try = 0.0
            self.flush()
            if not any(item == name for item, _ in self.spool.pending()):
                return Outcome("delivered", "screenshot.saved", "ok", {"name": name, "folder": self.display()})
            if isinstance(self.spool.last_error, AuthError):
                return Outcome("queued", "screenshot.auth_failed", "error", {"folder": self.display()})
            return Outcome("queued", "screenshot.queued", "warn", {"folder": self.display()})

    def _to_clipboard(self, image) -> None:
        if self.clipboard is None:
            return
        try:
            self.clipboard(image)
        except OSError as exc:
            log.warning("Copia dello screenshot negli appunti non riuscita: %s", exc)

    def display(self) -> str:
        if self.config.drive:
            root = self.config.drive
        else:
            root = f"\\\\{self.config.host}\\{self.config.share}"
        return "\\".join([root, *[p for p in self.config.subdir.split("/") if p]])

    def target(self) -> str:
        return f"smb://{self.config.host}/{self.config.share}".lower()

    def authenticate(self) -> None:
        if self.connected or not self.config.host or self.connect is None or self.vault is None:
            return
        try:
            login = self.vault.login(self.target())
        except (CredentialError, ValueError, OSError) as exc:
            raise sink.SinkError(f"vault:{type(exc).__name__}") from exc
        if login is None:
            return
        self.connect(f"\\\\{self.config.host}\\{self.config.share}", login.user, login.password)
        self.connected = True

    def directory(self) -> Path:
        return sink.resolve(sink.unc_root(self.config), self.config.subdir)

    def deliver(self, name: str, data: bytes) -> None:
        try:
            self.authenticate()
            sink.put(self.directory(), name, data)
        except (sink.SinkError, OSError):
            self.connected = False
            raise

    def flush(self) -> tuple:
        if not self.config.active:
            return 0, False
        return self.spool.flush(self.deliver)

    def retry(self) -> int:
        if not self.spool.pending() or not self.spool.ready():
            return 0
        delivered, failed = self.flush()
        if delivered:
            self.say(Outcome("delivered", "screenshot.delivered_later", "ok", {"count": delivered, "folder": self.display()}))
        if failed and isinstance(self.spool.last_error, AuthError) and not self.auth_warned:
            self.auth_warned = True
            self.say(Outcome("queued", "screenshot.auth_failed", "error", {"folder": self.display()}))
        return delivered

    def prune(self) -> int:
        if not self.config.active:
            return 0
        try:
            directory = self.directory()
            names = rules.doomed(sink.listing(directory), self.config.days, self.config.max_files, time.time())
            for name in names:
                sink.remove(directory, name)
            return len(names)
        except (sink.SinkError, OSError) as exc:
            log.info("Pulizia degli screenshot rimandata: %s", exc)
            return 0

    def start(self) -> None:
        self.worker = threading.Thread(target=self._run, daemon=True, name="screenshot-queue")
        self.worker.start()

    def _run(self) -> None:
        last_prune = 0.0
        while not self.stop_event.wait(FLUSH_EVERY):
            with self.lock:
                self.retry()
            if time.monotonic() - last_prune >= PRUNE_EVERY:
                last_prune = time.monotonic()
                self.prune()

    def stop(self) -> None:
        self.stop_event.set()
        if self.hotkey is not None:
            self.hotkey.stop()
