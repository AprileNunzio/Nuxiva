import asyncio
import logging
import re
import shutil
import time

try:
    from agenti.ear.mic_array import MAX_CHANNELS, MicArray
except ImportError:
    try:
        from mic_array import MAX_CHANNELS, MicArray
    except ImportError:
        from installer_wizard.agenti.ear.mic_array import MAX_CHANNELS, MicArray

log = logging.getLogger("nuxiva.ear.array")
FRAME_BYTES = 960
STALL_S = 0.6
MAX_SKEW_BYTES = 16000 * 2 * 3 // 10
MAX_BUFFER_BYTES = 16000 * 2 * 2
LIST_TIMEOUT = 4.0
SOURCE_RE = re.compile(r"^[A-Za-z0-9_.:@+\-]{1,200}$")
SKIP_RE = re.compile(r"\.monitor$|^auto_null|echo-cancel-source-monitor", re.I)


def parse_sources(listing: str) -> list[str]:
    names: list[str] = []
    for line in listing.splitlines():
        parts = line.split("\t")
        if len(parts) < 2:
            continue
        name = parts[1].strip()
        if SOURCE_RE.fullmatch(name) and not SKIP_RE.search(name) and name not in names:
            names.append(name)
    return names[:MAX_CHANNELS]


async def discover(prefix: list[str]) -> list[str]:
    if not shutil.which("pactl") or not shutil.which("parec"):
        return []
    try:
        process = await asyncio.create_subprocess_exec(
            *prefix, "pactl", "list", "short", "sources",
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL, stdin=asyncio.subprocess.DEVNULL)
        out, _ = await asyncio.wait_for(process.communicate(), LIST_TIMEOUT)
    except (OSError, asyncio.TimeoutError) as exc:
        log.info("Elenco dei microfoni non disponibile: %s", exc)
        return []
    return parse_sources(out.decode("utf-8", "replace")) if process.returncode == 0 else []


def source_command(prefix: list[str], name: str, latency_ms: int) -> list[str]:
    if not SOURCE_RE.fullmatch(name):
        raise ValueError("ear.array.source")
    return [*prefix, "parec", f"--device={name}", "--rate=16000", "--channels=1", "--format=s16le",
            f"--latency-msec={latency_ms}"]


class _Feed:

    def __init__(self, name: str) -> None:
        self.name = name
        self.buf = bytearray()
        self.last = time.monotonic()
        self.process: asyncio.subprocess.Process | None = None
        self.task: asyncio.Task | None = None
        self.done = False


class ArrayCapture:

    def __init__(self, sources: list[str], prefix: list[str], latency_ms: int) -> None:
        self.feeds = [_Feed(name) for name in sources[:MAX_CHANNELS]]
        self.prefix = prefix
        self.latency_ms = latency_ms
        self.array = MicArray(len(self.feeds))
        self.ready = asyncio.Event()
        self.running = False
        self.announced = -1

    async def start(self) -> None:
        self.running = True
        for feed in self.feeds:
            feed.process = await asyncio.create_subprocess_exec(
                *source_command(self.prefix, feed.name, self.latency_ms),
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL, stdin=asyncio.subprocess.DEVNULL)
            feed.task = asyncio.create_task(self._read(feed))
        log.info("Ascolto con %d microfoni insieme: %s", len(self.feeds), ", ".join(f.name for f in self.feeds))

    async def _read(self, feed: _Feed) -> None:
        try:
            if feed.process is None or feed.process.stdout is None:
                return
            while self.running:
                chunk = await feed.process.stdout.read(FRAME_BYTES * 2)
                if not chunk:
                    break
                feed.buf.extend(chunk)
                if len(feed.buf) > MAX_BUFFER_BYTES:
                    del feed.buf[:len(feed.buf) - MAX_BUFFER_BYTES]
                feed.last = time.monotonic()
                self.ready.set()
        except OSError as exc:
            log.warning("Microfono %s non leggibile: %s", feed.name, exc)
        finally:
            feed.done = True
            self.ready.set()

    def alive(self) -> bool:
        return self.running and any(not f.done for f in self.feeds)

    def _take(self) -> bytes | None:
        now = time.monotonic()
        live = [f for f in self.feeds if not f.done and now - f.last < STALL_S]
        if not live or any(len(f.buf) < FRAME_BYTES for f in live):
            return None
        frames = []
        for feed in self.feeds:
            if feed in live:
                frames.append(bytes(feed.buf[:FRAME_BYTES]))
                del feed.buf[:FRAME_BYTES]
                if len(feed.buf) > MAX_SKEW_BYTES:
                    del feed.buf[:len(feed.buf) - MAX_SKEW_BYTES]
            else:
                frames.append(bytes(FRAME_BYTES))
        mixed = self.array.mix_pcm(frames)
        if self.array.best != self.announced:
            self.announced = self.array.best
            log.info("Microfono che sente meglio: %s (uniti %d)", self.feeds[self.array.best].name, self.array.fused)
        return mixed

    async def read(self) -> bytes:
        while self.alive():
            out = bytearray()
            while (frame := self._take()) is not None:
                out.extend(frame)
            if out:
                return bytes(out)
            self.ready.clear()
            try:
                await asyncio.wait_for(self.ready.wait(), STALL_S)
            except asyncio.TimeoutError:
                continue
        return b""

    async def stop(self) -> None:
        self.running = False
        for feed in self.feeds:
            process, feed.process = feed.process, None
            if process is not None and process.returncode is None:
                try:
                    process.terminate()
                    await asyncio.wait_for(process.wait(), 1.0)
                except ProcessLookupError:
                    log.debug("Microfono %s già chiuso", feed.name)
                except asyncio.TimeoutError:
                    process.kill()
                    await process.wait()
            if feed.task is not None:
                feed.task.cancel()
                await asyncio.gather(feed.task, return_exceptions=True)
                feed.task = None
