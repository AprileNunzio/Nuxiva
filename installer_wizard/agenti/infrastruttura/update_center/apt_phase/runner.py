from __future__ import annotations

import asyncio
import fcntl
import os
import shutil
import sys
import time
from pathlib import Path
from typing import Callable, Optional

from config import DEMO, STATE_DIR, env_get

from agenti.update_center import system_runner

from . import stream
from .state import AptPhase, phase

LOCK_FILE = STATE_DIR / "apt_phase.lock"
UPDATE_TIMEOUT = 600.0
UPGRADE_TIMEOUT = 3600.0
TOUCH_INTERVAL = 0.25
Event = Callable[[str, str], None]
Touch = Callable[[], None]
_lock = asyncio.Lock()


def enabled() -> bool:
    return env_get("NUXIVA_UPDATE_APT", "1") != "0"


def skip_reason() -> Optional[str]:
    if not enabled():
        return "disabled"
    if DEMO or os.environ.get("NUXIVA_TEST_AUTH") == "1":
        return "test_env"
    if not sys.platform.startswith("linux") or not shutil.which("apt-get"):
        return "no_apt"
    if os.geteuid() != 0:
        return "not_root"
    return None


def commands() -> tuple[list[str], list[str]]:
    return (system_runner.apt_command("update"),
            system_runner.apt_command("-y", "--with-new-pkgs", "upgrade"))


class _Throttle:
    def __init__(self, touch: Touch) -> None:
        self.touch = touch
        self.last = 0.0

    def __call__(self, force: bool = False) -> None:
        now = time.monotonic()
        if force or now - self.last >= TOUCH_INTERVAL:
            self.last = now
            self.touch()


def _acquire(path: Path) -> Optional[int]:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        os.close(fd)
        return None
    return fd


def _release(fd: int) -> None:
    fcntl.flock(fd, fcntl.LOCK_UN)
    os.close(fd)


async def _step(target: AptPhase, name: str, cmd: list[str], timeout: float, notify: _Throttle) -> bool:
    target.step(name, "running")
    notify(True)

    def on_line(raw: str) -> None:
        target.feed(raw)
        notify()

    try:
        code = await stream.run(cmd, on_line, timeout)
    except stream.StreamTimeout as exc:
        target.feed(f"E: {exc}")
        code = -1
    except OSError as exc:
        target.feed(f"E: {type(exc).__name__}")
        code = -1
    target.step(name, "done" if code == 0 else "failed")
    notify(True)
    return code == 0


async def _execute(target: AptPhase, event: Event, notify: _Throttle) -> str:
    update_cmd, upgrade_cmd = commands()
    target.begin()
    event("INFO", "Aggiornamento dei pacchetti di sistema (apt) avviato")
    updated = await _step(target, "update", update_cmd, UPDATE_TIMEOUT, notify)
    upgraded = await _step(target, "upgrade", upgrade_cmd, UPGRADE_TIMEOUT, notify)
    if updated and upgraded:
        target.finish("done")
        event("INFO", "Pacchetti di sistema aggiornati: si prosegue con Nuxiva")
        return "done"
    failed = "apt_update" if not updated else "apt_upgrade"
    target.finish("failed", failed)
    event("ERROR", f"Aggiornamento dei pacchetti di sistema non riuscito ({failed}): si prosegue con Nuxiva")
    return "failed"


async def run(event: Event, touch: Touch, target: AptPhase = phase) -> str:
    reason = skip_reason()
    if reason:
        target.skip(reason)
        touch()
        return "skipped"
    if _lock.locked():
        return "busy"
    async with _lock:
        fd = _acquire(LOCK_FILE)
        if fd is None:
            event("WARN", "Aggiornamento apt già in corso altrove: fase saltata")
            return "busy"
        notify = _Throttle(touch)
        try:
            return await _execute(target, event, notify)
        except asyncio.CancelledError:
            target.finish("failed", "cancelled")
            raise
        finally:
            target.close()
            _release(fd)
            notify(True)
