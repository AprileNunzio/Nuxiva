import asyncio
import logging

from features.ear.host_mic import get_capture_candidates

log = logging.getLogger("nuxiva.ear.mictest")
RATE = 16000
FIRST_CHUNK_TIMEOUT = 2.5
READ_TIMEOUT = 2.0
STOP_TIMEOUT = 1.0
BUSY_WAIT = 3.0
LOCK = asyncio.Lock()


class MicUnavailable(RuntimeError):
    pass


class MicBusy(RuntimeError):
    pass


class MicSource:

    def __init__(self) -> None:
        self.process: asyncio.subprocess.Process | None = None
        self.carry = b""
        self.first = b""

    async def __aenter__(self) -> "MicSource":
        try:
            await asyncio.wait_for(LOCK.acquire(), BUSY_WAIT)
        except asyncio.TimeoutError as exc:
            raise MicBusy("mic_busy") from exc
        try:
            await self._open()
        except BaseException:
            LOCK.release()
            raise
        return self

    async def __aexit__(self, *_exc) -> None:
        try:
            await self._close()
        finally:
            LOCK.release()

    async def _open(self) -> None:
        failures = []
        for cmd in get_capture_candidates():
            try:
                self.process = await asyncio.create_subprocess_exec(
                    *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL, stdin=asyncio.subprocess.DEVNULL)
                if self.process.stdout is None:
                    raise OSError("stdout")
                self.first = await asyncio.wait_for(self.process.stdout.read(4096), FIRST_CHUNK_TIMEOUT)
            except (OSError, asyncio.TimeoutError) as exc:
                failures.append(f"{cmd[0]}: {exc.__class__.__name__}")
                self.first = b""
            if self.first:
                return
            await self._close()
        log.warning("Test del microfono: nessuna sorgente disponibile (%s)", ", ".join(failures) or "nessun comando")
        raise MicUnavailable("mic_unavailable")

    async def read(self, size: int) -> bytes:
        if self.process is None or self.process.stdout is None:
            raise MicUnavailable("mic_unavailable")
        data, self.first = self.first, b""
        while len(self.carry) + len(data) < size:
            try:
                chunk = await asyncio.wait_for(self.process.stdout.read(size), READ_TIMEOUT)
            except asyncio.TimeoutError as exc:
                raise MicUnavailable("mic_stalled") from exc
            if not chunk:
                raise MicUnavailable("mic_closed")
            data += chunk
        buffer = self.carry + data
        self.carry = buffer[size:]
        return buffer[:size]

    async def record(self, seconds: float) -> bytes:
        total = int(RATE * seconds) * 2
        parts, got = [], 0
        while got < total:
            block = await self.read(min(3200, total - got))
            parts.append(block)
            got += len(block)
        return b"".join(parts)

    async def _close(self) -> None:
        process, self.process = self.process, None
        if process is None:
            return
        try:
            process.terminate()
        except ProcessLookupError:
            return
        try:
            await asyncio.wait_for(process.wait(), STOP_TIMEOUT)
        except asyncio.TimeoutError:
            try:
                process.kill()
            except ProcessLookupError:
                return
            await process.wait()
