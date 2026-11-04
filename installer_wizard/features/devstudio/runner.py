import asyncio
import os
import shutil
import sys
from pathlib import Path

from features.devstudio.workspace import DevError, safe_path

try:
    import resource
except ImportError:
    resource = None

TIMEOUT = 60
OUTPUT_LIMIT = 20000
CHECKS = {
    "python_tests": ("python3", "-I", "-m", "unittest", "discover", "-s", ".", "-p", "test_*.py"),
    "python_compile": ("python3", "-I", "-m", "compileall", "-q", "."),
    "node_tests": ("node", "--test"),
}
ENTRY = {"python_run": ("python3", "-I"), "node_run": ("node",)}
EXTENSIONS = {"python_run": ".py", "node_run": ".js"}
LIMITS = ((resource.RLIMIT_CPU, 60), (resource.RLIMIT_FSIZE, 20 * 1024 * 1024), (resource.RLIMIT_NOFILE, 256), (resource.RLIMIT_NPROC, 128)) if resource else ()
ISOLATION_MISSING = "isolamento di rete non disponibile (manca unshare): non eseguo codice scritto da un agente"


def names() -> list[str]:
    return [*CHECKS, *ENTRY]


def _limit() -> None:
    if resource is None:
        raise DevError(ISOLATION_MISSING)
    os.setsid()
    for kind, value in LIMITS:
        resource.setrlimit(kind, (value, value))


def command(check: str, folder: Path, entry: str) -> list[str]:
    if check in CHECKS:
        base = list(CHECKS[check])
    elif check in ENTRY:
        target = safe_path(folder, entry)
        if target.suffix != EXTENSIONS[check] or not target.is_file():
            raise DevError(f"serve un file {EXTENSIONS[check]} esistente nel progetto")
        base = [*ENTRY[check], target.relative_to(folder).as_posix()]
    else:
        raise DevError(f"controllo sconosciuto: {', '.join(names())}")
    program = shutil.which(base[0])
    if not program:
        raise DevError(f"{base[0]} non è installato sul server")
    return [program, *base[1:]]


def environment(folder: Path) -> dict:
    return {"PATH": "/usr/local/bin:/usr/bin:/bin", "HOME": str(folder), "LANG": "C.UTF-8", "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONIOENCODING": "utf-8", "NODE_ENV": "test"}


async def run(check: str, folder: Path, entry: str = "") -> tuple[int, str]:
    argv = command(check, folder, entry)
    if resource is None or sys.platform != "linux" or not shutil.which("unshare"):
        raise DevError(ISOLATION_MISSING)
    process = await asyncio.create_subprocess_exec(
        shutil.which("unshare"), "--net", "--", *argv, cwd=folder, env=environment(folder), stdin=asyncio.subprocess.DEVNULL,
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT, preexec_fn=_limit)
    try:
        data, _ = await asyncio.wait_for(process.communicate(), TIMEOUT)
    except asyncio.TimeoutError:
        process.kill()
        await process.wait()
        return 124, f"interrotto dopo {TIMEOUT} secondi"
    text = data.decode("utf-8", errors="replace")
    return process.returncode or 0, text[-OUTPUT_LIMIT:]
