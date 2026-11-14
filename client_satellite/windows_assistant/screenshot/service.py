import itertools
import logging
import os
import socket
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

from screenshot import capture, rules, sink
from screenshot.spool import Spool

log = logging.getLogger("nuxiva.screenshot")
DEBOUNCE = 1.5
FLUSH_EVERY = 5
PRUNE_EVERY = 3600


class Service:
    def __init__(self, spool_dir: Path, notify, text, guest_flag: Path | None = None, hotkey_factory=None) -> None:
        self.config = rules.Config()
        self.spool = Spool(spool_dir)
        self.notify = notify
        self.text = text
        self.guest_flag = guest_flag or Path(os.environ.get("ProgramData", ".")) / "Nuxiva" / "guests-present"
        self.counter = itertools.count()
        self.last = 0.0
        self.lock = threading.Lock()
        self.stop_event = threading.Event()
        self.hotkey = None
        self.hotkey_factory = hotkey_factory
        self.worker: threading.Thread | None = None

    def apply(self, settings: dict) -> None:
        config = rules.from_settings(settings)
        if config == self.config:
            return
        self.config = config
        if config.enabled and self.hotkey is None and self.hotkey_factory:
            self.hotkey = self.hotkey_factory(self.trigger)
            if not self.hotkey.start():
                log.warning("Tasto Stamp già occupato da un altro programma")
        if not config.enabled and self.hotkey is not None:
            self.hotkey.stop()
            self.hotkey = None

    def guests(self) -> bool:
        try:
            return self.guest_flag.read_text(encoding="ascii", errors="ignore").strip() in ("1", "true", "yes")
        except OSError:
            return False

    def denied(self, locked: bool) -> str | None:
        if not self.config.enabled:
            return "disabled"
        if not self.config.active:
            return "target"
        if self.config.block_locked and locked:
            return "locked"
        if self.config.block_guests and self.guests():
            return "guests"
        return None

    def trigger(self) -> None:
        now = time.monotonic()
        if now - self.last < DEBOUNCE:
            return
        self.last = now
        threading.Thread(target=self.capture_once, daemon=True, name="screenshot").start()

    def say(self, key: str) -> None:
        if self.config.notice:
            self.notify(self.text(key))

    def capture_once(self, locked: bool | None = None) -> str:
        with self.lock:
            reason = self.denied(capture.locked() if locked is None else locked)
            if reason:
                if reason != "disabled":
                    self.say("screenshot.blocked")
                return reason
            try:
                image = capture.grab()
                capture.apply_masks(image, self.config.masks)
                data = capture.png(image)
                name = rules.file_name(socket.gethostname(), datetime.now(timezone.utc), next(self.counter))
                self.spool.enqueue(name, data)
            except (capture.CaptureError, sink.SinkError, OSError) as exc:
                log.warning("Screenshot non riuscito: %s", exc)
                self.say("screenshot.failed")
                return "failed"
            delivered, failed = self.flush()
            queued = failed or bool(self.spool.pending())
            self.say("screenshot.queued" if queued else "screenshot.saved")
            return "queued" if queued else "delivered"

    def directory(self) -> Path:
        return sink.resolve(sink.unc_root(self.config), self.config.subdir)

    def deliver(self, name: str, data: bytes) -> None:
        sink.put(self.directory(), name, data)

    def flush(self) -> tuple:
        if not self.config.active:
            return 0, False
        return self.spool.flush(self.deliver)

    def prune(self) -> int:
        if not self.config.active:
            return 0
        try:
            directory = self.directory()
            names = rules.doomed(sink.listing(directory), self.config.days, self.config.max_files, time.time())
            for name in names:
                sink.remove(directory, name)
            return len(names)
        except (sink.SinkError, OSError):
            return 0

    def start(self) -> None:
        self.worker = threading.Thread(target=self._run, daemon=True, name="screenshot-queue")
        self.worker.start()

    def _run(self) -> None:
        last_prune = 0.0
        while not self.stop_event.wait(FLUSH_EVERY):
            if self.spool.pending():
                self.flush()
            if time.monotonic() - last_prune >= PRUNE_EVERY:
                last_prune = time.monotonic()
                self.prune()

    def stop(self) -> None:
        self.stop_event.set()
        if self.hotkey is not None:
            self.hotkey.stop()
