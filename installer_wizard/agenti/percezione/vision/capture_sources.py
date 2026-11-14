import logging
import os
import shutil
import subprocess

import cv2
import numpy as np

log = logging.getLogger("nuxiva.vision.capture")

MAX_TITLE = 160
RUN_TIMEOUT = 2.0


def _run(argv: list[str]) -> str:
    try:
        done = subprocess.run(argv, capture_output=True, text=True, timeout=RUN_TIMEOUT, check=False, shell=False)
    except (OSError, subprocess.TimeoutExpired):
        return ""
    return done.stdout.strip()[:MAX_TITLE] if done.returncode == 0 else ""


def active_window() -> tuple[str, str] | None:
    tool = shutil.which("xdotool")
    if tool is None or not os.environ.get("DISPLAY"):
        return None
    title = _run([tool, "getactivewindow", "getwindowname"])
    pid = _run([tool, "getactivewindow", "getwindowpid"])
    app = ""
    if pid.isdigit():
        try:
            with open(f"/proc/{int(pid)}/comm", encoding="utf-8", errors="ignore") as handle:
                app = handle.read(64).strip()
        except OSError:
            app = ""
    if not title and not app:
        return None
    return app or "unknown", title


def grab_screen() -> np.ndarray | None:
    try:
        import mss
    except ImportError:
        return None
    try:
        with mss.mss() as shot:
            frame = shot.grab(shot.monitors[0])
    except (OSError, ValueError, KeyError, IndexError) as exc:
        log.warning("Cattura dello schermo non riuscita: %s", exc)
        return None
    return cv2.cvtColor(np.asarray(frame), cv2.COLOR_BGRA2BGR)
