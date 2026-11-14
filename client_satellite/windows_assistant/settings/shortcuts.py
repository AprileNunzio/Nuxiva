import logging
import os
import subprocess
from pathlib import Path

from settings import agent_name, paths

log = logging.getLogger("nuxiva.shortcuts")
NO_WINDOW = 0x08000000
SCRIPT = ("$s=(New-Object -ComObject WScript.Shell).CreateShortcut($env:NUXIVA_LNK);"
          "$s.TargetPath=$env:NUXIVA_TARGET;$s.WorkingDirectory=$env:NUXIVA_DIR;"
          "$s.IconLocation=$env:NUXIVA_TARGET+',0';$s.Description=$env:NUXIVA_DESC;$s.Save()")


def folder() -> Path:
    base = os.environ.get("ProgramData", r"C:\ProgramData")
    return Path(base) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Nuxiva"


def sync(previous: str, current: str) -> bool:
    if not paths.FROZEN:
        return True
    from pathlib import Path as P
    import sys
    target = P(sys.executable).resolve()
    start = folder()
    old, new = agent_name.shortcut_file(previous), agent_name.shortcut_file(current)
    if old and old != new and (start / old).is_file():
        (start / old).unlink()
    if not new or (start / new).is_file():
        return True
    start.mkdir(parents=True, exist_ok=True)
    env = {**os.environ, "NUXIVA_LNK": str(start / new), "NUXIVA_TARGET": str(target),
           "NUXIVA_DIR": str(target.parent), "NUXIVA_DESC": agent_name.display(current)}
    result = subprocess.run(["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", SCRIPT], env=env,
                            capture_output=True, creationflags=NO_WINDOW, check=False, timeout=30)
    if result.returncode != 0:
        log.error("Collegamento del menu Start non creato: %s", result.stderr.decode(errors="replace").strip())
        return False
    return True
