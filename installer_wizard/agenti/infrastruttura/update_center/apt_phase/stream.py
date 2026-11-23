from __future__ import annotations

import asyncio
import os
import signal
from typing import Callable, List, Sequence

CHUNK = 4096
MAX_PENDING = 16 * 1024
SAFE_PATH = "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"


class StreamTimeout(Exception):
    pass


def _split(buffer: bytes) -> tuple[List[bytes], bytes]:
    parts = buffer.replace(b"\r\n", b"\n").split(b"\n")
    pending = parts.pop()
    if len(pending) > MAX_PENDING:
        parts.append(pending)
        pending = b""
    return parts, pending


def _kill(proc: asyncio.subprocess.Process) -> None:
    try:
        os.killpg(proc.pid, signal.SIGTERM)
    except ProcessLookupError:
        return


async def _pump(proc: asyncio.subprocess.Process, on_line: Callable[[str], None]) -> None:
    assert proc.stdout is not None
    pending = b""
    while chunk := await proc.stdout.read(CHUNK):
        lines, pending = _split(pending + chunk)
        for raw in lines:
            on_line(raw.decode("utf-8", errors="replace"))
    if pending:
        on_line(pending.decode("utf-8", errors="replace"))


async def run(cmd: Sequence[str], on_line: Callable[[str], None], timeout: float) -> int:
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdin=asyncio.subprocess.DEVNULL,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
        start_new_session=True,
        env={"PATH": SAFE_PATH, "LANG": "C.UTF-8"},
    )
    try:
        await asyncio.wait_for(_pump(proc, on_line), timeout)
        return await asyncio.wait_for(proc.wait(), 30)
    except asyncio.TimeoutError as exc:
        _kill(proc)
        await proc.wait()
        raise StreamTimeout(f"timeout dopo {int(timeout)} s") from exc
    except asyncio.CancelledError:
        _kill(proc)
        raise
