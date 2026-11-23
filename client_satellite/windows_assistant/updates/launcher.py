import ctypes
import subprocess
import sys
from pathlib import Path

from updates.errors import UpdateFailure

SILENT = ("/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART", "/CLOSEAPPLICATIONS")
ELEVATION_REQUIRED = 740
DETACHED = 0x00000008 | 0x00000200


def _elevated(installer: Path) -> None:
    result = ctypes.windll.shell32.ShellExecuteW(None, "runas", str(installer), " ".join(SILENT), str(installer.parent), 0)
    if result <= 32:
        raise UpdateFailure("install_blocked", f"ShellExecute {result}")


def launch(installer: Path) -> None:
    flags = DETACHED if sys.platform == "win32" else 0
    try:
        subprocess.Popen([str(installer), *SILENT], close_fds=True, creationflags=flags, cwd=str(installer.parent))
    except OSError as exc:
        if getattr(exc, "winerror", None) == ELEVATION_REQUIRED:
            _elevated(installer)
            return
        raise UpdateFailure("install_blocked", exc.strerror or type(exc).__name__) from exc
