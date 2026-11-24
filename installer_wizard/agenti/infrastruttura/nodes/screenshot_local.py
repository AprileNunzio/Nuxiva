import os
import re
import secrets
import shutil
import socket
import stat
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

from config import read_env

DEFAULT_ROOT = "/srv/nuxiva/condivisa"
DEFAULT_SUBDIR = "05 Scambio/Screenshot"
ALLOWED_ROOTS = ("/srv/nuxiva", "/mnt", "/media", "/run/media")
GUEST_FLAG = Path("/run/nuxiva/guests-present")
DISPLAY = ":0"
TIMEOUT = 10
MAX_BYTES = 64 * 1024 * 1024
PNG = b"\x89PNG\r\n\x1a\n"
SEGMENT = re.compile(r"^[A-Za-z0-9_-][A-Za-z0-9 ._-]{0,62}[A-Za-z0-9_-]$|^[A-Za-z0-9_-]$")
TOOLS = (("maim", ["--format", "png", "--hidecursor"]), ("scrot", ["--silent", "--overwrite", "/dev/stdout"]),
         ("import", ["-window", "root", "png:-"]))


class LocalError(Exception):
    def __init__(self, status: str, reason: str = "") -> None:
        super().__init__(reason or status)
        self.status = status


def host_label(raw: str) -> str:
    out = ""
    for char in raw.lower():
        if char.isascii() and char.isalnum():
            out += char
        elif char in "-_. " and out and not out.endswith("-"):
            out += "-"
        if len(out) >= 40:
            break
    return out.strip("-") or "nodo"


def file_name(seq: int, now: float | None = None) -> str:
    when = datetime.fromtimestamp(time.time() if now is None else now, timezone.utc)
    return f"{host_label(socket.gethostname())}_{when:%Y%m%d-%H%M%S}_{seq % 1000:03d}.png"


def valid_subdir(subdir: str) -> bool:
    parts = subdir.split("/") if subdir else []
    return len(parts) <= 4 and all(SEGMENT.match(p) and not p.endswith((".", " ")) for p in parts)


def settings(env: dict | None = None) -> tuple[Path, str]:
    env = env if env is not None else read_env()
    flag = str(env.get("NUXIVA_SCREENSHOT") or "").strip()
    if flag == "0" or (not flag and str(env.get("NUXIVA_SHARES") or "1").strip() == "0"):
        raise LocalError("disabled")
    if str(env.get("NUXIVA_SCREENSHOT_MASK") or "").strip():
        raise LocalError("blocked", "mask")
    target = str(env.get("NUXIVA_SCREENSHOT_TARGET") or "").strip() or DEFAULT_ROOT
    if target.startswith("smb://"):
        raise LocalError("failed", "smb_needs_service")
    subdir = str(env.get("NUXIVA_SCREENSHOT_SUBDIR") or "").strip() or DEFAULT_SUBDIR
    if not valid_subdir(subdir):
        raise LocalError("no_target", "subdir")
    root = Path(os.path.realpath(target))
    if not any(root == Path(r) or Path(r) in root.parents for r in ALLOWED_ROOTS):
        raise LocalError("no_target", "root")
    return root, subdir


def directory(root: Path, subdir: str) -> Path:
    if not root.is_dir():
        raise LocalError("queued", "root_missing")
    current = root
    for part in [p for p in subdir.split("/") if p]:
        current = current / part
        try:
            info = os.lstat(current)
        except FileNotFoundError:
            current.mkdir(mode=0o2775)
            continue
        if stat.S_ISLNK(info.st_mode) or not stat.S_ISDIR(info.st_mode):
            raise LocalError("failed", "unsafe")
    return current


def grab(display: str = DISPLAY) -> bytes:
    env = {"PATH": "/usr/local/bin:/usr/bin:/bin", "DISPLAY": display, "HOME": "/root"}
    if Path("/root/.Xauthority").is_file():
        env["XAUTHORITY"] = "/root/.Xauthority"
    for tool, args in TOOLS:
        binary = shutil.which(tool, path=env["PATH"])
        if not binary:
            continue
        try:
            done = subprocess.run([binary, *args], env=env, capture_output=True, timeout=TIMEOUT, check=False)
        except (OSError, subprocess.TimeoutExpired):
            continue
        if done.returncode == 0 and done.stdout.startswith(PNG) and len(done.stdout) <= MAX_BYTES:
            return done.stdout
    raise LocalError("failed", "no_backend")


def store(folder: Path, name: str, data: bytes) -> Path:
    final = folder / name
    temp = folder / f".tmp-{secrets.token_hex(8)}"
    try:
        fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o664)
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.link(temp, final)
    except FileExistsError as exc:
        raise LocalError("failed", "exists") from exc
    except OSError as exc:
        raise LocalError("queued", type(exc).__name__) from exc
    finally:
        if temp.exists():
            temp.unlink()
    return final


def capture(seq: int, env: dict | None = None, grabber=None) -> dict:
    root, subdir = settings(env)
    if GUEST_FLAG.is_file() and GUEST_FLAG.read_text(encoding="ascii", errors="ignore").strip() in ("1", "true", "yes"):
        raise LocalError("blocked", "guests")
    folder = directory(root, subdir)
    data = (grabber or grab)()
    name = file_name(seq)
    store(folder, name, data)
    return {"status": "saved", "name": name, "folder": str(folder)}
