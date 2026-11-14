import struct
from collections import deque

AUDIO_KIND = 1
MAX_WAV_BYTES = 16 * 1024 * 1024
MIN_RATE_HZ = 8000
MAX_RATE_HZ = 48000
MAX_FRAME_BYTES = 4096
MAX_QUEUE_FRAMES = 4096


def native():
    try:
        import nuxiva_native
    except ImportError:
        return None
    return getattr(nuxiva_native, "RustPacer", None)


def _fmt(body: bytes) -> tuple:
    if len(body) < 16:
        raise ValueError("duplex.parse")
    tag, channels, rate = struct.unpack_from("<HHI", body, 0)
    (bits,) = struct.unpack_from("<H", body, 14)
    if tag != 1 or bits != 16 or channels not in (1, 2) or not MIN_RATE_HZ <= rate <= MAX_RATE_HZ:
        raise ValueError("duplex.invalid")
    return channels, rate


def parse_wav(data: bytes) -> tuple:
    if len(data) > MAX_WAV_BYTES:
        raise ValueError("duplex.too_large")
    if data[:4] != b"RIFF" or data[8:12] != b"WAVE":
        raise ValueError("duplex.invalid")
    at, fmt = 12, None
    while len(data) >= at + 4:
        if len(data) < at + 8:
            raise ValueError("duplex.parse")
        chunk_id, declared = data[at:at + 4], struct.unpack_from("<I", data, at + 4)[0]
        start = at + 8
        available = len(data) - start
        if chunk_id == b"data":
            if fmt is None:
                raise ValueError("duplex.invalid")
            body = data[start:start + min(declared, available)]
            channels, rate = fmt
            count = len(body) // (2 * channels)
            if count == 0:
                raise ValueError("duplex.invalid")
            raw = struct.unpack(f"<{count * channels}h", body[: count * channels * 2])
            if channels == 1:
                return rate, list(raw)
            return rate, [int((raw[i] + raw[i + 1]) / 2) for i in range(0, len(raw), 2)]
        if declared > available:
            raise ValueError("duplex.parse")
        if chunk_id == b"fmt ":
            fmt = _fmt(data[start:start + declared])
        at = start + declared + (declared & 1)
    raise ValueError("duplex.invalid")


class PyPacer:
    def __init__(self, frame_ms: int = 40, lead_ms: int = 240):
        if not (10 <= frame_ms <= 100 and frame_ms <= lead_ms <= 1000):
            raise ValueError("duplex.settings.invalid")
        self._frame_ms, self._lead_us = frame_ms, lead_ms * 1000
        self._queue: deque = deque()
        self._horizon = 0

    def push_wav(self, epoch: int, seq: int, wav: bytes) -> tuple:
        rate, samples = parse_wav(wav)
        per_frame = max(1, min(rate * self._frame_ms // 1000, MAX_FRAME_BYTES // 2))
        count = -(-len(samples) // per_frame)
        if len(self._queue) + count > MAX_QUEUE_FRAMES:
            raise ValueError("duplex.capacity")
        for i in range(0, len(samples), per_frame):
            part = samples[i:i + per_frame]
            head = bytes([AUDIO_KIND]) + epoch.to_bytes(4, "big") + seq.to_bytes(4, "big")
            self._queue.append((epoch, head + struct.pack(f"<{len(part)}h", *part), len(part) * 1_000_000 // rate))
        return rate, count, len(samples) * 1_000_000 // rate // 1000

    def poll(self, now_ms: int, live_epoch: int) -> list:
        now_us, out = now_ms * 1000, []
        while self._queue:
            epoch, frame, us = self._queue[0]
            if epoch != live_epoch:
                self._queue.popleft()
                continue
            if self._horizon > now_us + self._lead_us:
                break
            self._queue.popleft()
            self._horizon = max(self._horizon, now_us) + us
            out.append(frame)
        return out

    def cancel(self) -> tuple:
        dropped = (len(self._queue), sum(item[2] for item in self._queue) // 1000)
        self._queue.clear()
        self._horizon = 0
        return dropped

    def queued(self) -> int:
        return len(self._queue)

    def in_flight_ms(self, now_ms: int) -> int:
        return max(0, self._horizon - now_ms * 1000) // 1000


def build(frame_ms: int = 40, lead_ms: int = 240):
    klass = native()
    return klass(frame_ms, lead_ms) if klass is not None else PyPacer(frame_ms, lead_ms)
