import asyncio
import functools
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from features.agency.forge.guard import ALLOWED_IMPORTS, check

try:
    import resource
except ImportError:
    resource = None

HARNESS = Path(__file__).resolve().parent / "harness.py"
TIMEOUT = 10.0
INPUT_LIMIT = 64 * 1024
OUTPUT_LIMIT = 64 * 1024
LIMITS = ((resource.RLIMIT_CPU, 5), (resource.RLIMIT_NOFILE, 32), (resource.RLIMIT_NPROC, 128),
          (resource.RLIMIT_CORE, 0)) if resource else ()


class SandboxUnavailable(RuntimeError):
    pass


def _limit() -> None:
    os.setsid()
    for kind, value in LIMITS:
        resource.setrlimit(kind, (value, value))


@functools.cache
def available() -> bool:
    if resource is None or sys.platform != "linux" or not shutil.which("unshare"):
        return False
    try:
        probe = subprocess.run([shutil.which("unshare"), "--net", "--", "/bin/true"], capture_output=True, timeout=5,
                               check=False)
    except (OSError, subprocess.TimeoutExpired):
        return False
    return probe.returncode == 0


async def execute(code: str, args: dict) -> dict:
    check(code)
    payload = json.dumps({"code": code, "args": args}, ensure_ascii=False).encode()
    if len(payload) > INPUT_LIMIT + len(code.encode()):
        return {"ok": False, "error": "arguments too large"}
    if not available():
        raise SandboxUnavailable("network isolation (unshare) is not available")
    with tempfile.TemporaryDirectory(prefix="nuxiva-forge-") as cell:
        os.chmod(cell, 0o700)
        process = await asyncio.create_subprocess_exec(
            shutil.which("unshare"), "--net", "--", sys.executable, "-I", "-B", "-S", str(HARNESS),
            ",".join(sorted(ALLOWED_IMPORTS)), cwd=cell, env={"PATH": "/usr/bin:/bin", "LANG": "C.UTF-8", "HOME": cell},
            stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL,
            preexec_fn=_limit)
        try:
            data, _ = await asyncio.wait_for(process.communicate(payload), TIMEOUT)
        except asyncio.TimeoutError:
            process.kill()
            await process.wait()
            return {"ok": False, "error": f"timeout after {TIMEOUT:.0f} s"}
    if len(data) > OUTPUT_LIMIT:
        return {"ok": False, "error": "result too large"}
    try:
        result = json.loads(data.decode("utf-8", errors="replace"))
    except ValueError:
        return {"ok": False, "error": f"tool crashed (exit {process.returncode})"}
    return result if isinstance(result, dict) else {"ok": False, "error": "invalid sandbox reply"}
