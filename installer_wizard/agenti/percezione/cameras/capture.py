import asyncio
import time

IDLE_SECONDS = 20.0
MAX_BUFFER = 6_000_000


class CameraCapture:
    def __init__(self, command):
        self.command = command
        self.latest = b""
        self.updated = 0.0
        self.requested = time.monotonic()
        self.ready = asyncio.Event()
        self.task = None

    async def read(self):
        self.requested = time.monotonic()
        if self.task is None or self.task.done():
            self.ready.clear()
            self.task = asyncio.create_task(self._run())
        if not self.latest or time.monotonic() - self.updated > 3:
            self.ready.clear()
            try:
                await asyncio.wait_for(self.ready.wait(), 12)
            except asyncio.TimeoutError:
                return b""
        return self.latest if time.monotonic() - self.updated <= 3 else b""

    async def _run(self):
        process = None
        try:
            process = await asyncio.create_subprocess_exec(
                *self.command, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL,
            )
            buffer = bytearray()
            while time.monotonic() - self.requested < IDLE_SECONDS:
                try:
                    chunk = await asyncio.wait_for(process.stdout.read(65536), 5)
                except asyncio.TimeoutError:
                    continue
                if not chunk:
                    break
                buffer.extend(chunk)
                while True:
                    start = buffer.find(b"\xff\xd8")
                    end = buffer.find(b"\xff\xd9", start + 2) if start >= 0 else -1
                    if end < 0:
                        break
                    self.latest = bytes(buffer[start:end + 2])
                    self.updated = time.monotonic()
                    del buffer[:end + 2]
                    self.ready.set()
                if len(buffer) > MAX_BUFFER:
                    buffer.clear()
        except OSError:
            self.latest = b""
        finally:
            if process is not None:
                if process.returncode is None:
                    try:
                        process.kill()
                    except ProcessLookupError:
                        pass
                await process.wait()
            self.ready.set()


_captures = {}


async def snapshot(source_id, command):
    key = (source_id, tuple(command))
    for old_key, capture in list(_captures.items()):
        if capture.task is not None and capture.task.done() and time.monotonic() - capture.requested > IDLE_SECONDS:
            _captures.pop(old_key, None)
    capture = _captures.get(key)
    if capture is None:
        capture = CameraCapture(command)
        _captures[key] = capture
    return await capture.read()
