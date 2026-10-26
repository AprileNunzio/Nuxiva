import asyncio
import re
import shutil
import time

from features.people.fingerprint.readers import readers

CACHE_SECONDS = 30.0
PATH_RE = re.compile(r'"(/net/reactivated/Fprint/Device/\d+)"')
_state = {"at": 0.0}


async def _devices() -> list[str]:
    tool = shutil.which("busctl")
    if not tool:
        return []
    process = await asyncio.create_subprocess_exec(
        tool, "--system", "call", "net.reactivated.Fprint", "/net/reactivated/Fprint/Manager",
        "net.reactivated.Fprint.Manager", "GetDevices", stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL)
    try:
        out, _ = await asyncio.wait_for(process.communicate(), timeout=5)
    except asyncio.TimeoutError:
        process.kill()
        await process.wait()
        return []
    return PATH_RE.findall(out.decode("utf-8", "replace")) if process.returncode == 0 else []


async def discover(now: float | None = None) -> int:
    now = now or time.time()
    if now - _state["at"] < CACHE_SECONDS:
        return 0
    _state["at"] = now
    found = await _devices()
    for path in found:
        readers.seen("server", "", path.rsplit("/", 1)[-1], "usb", "Server", now, ready=False)
    return len(found)
