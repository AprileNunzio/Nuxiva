from dataclasses import dataclass

import native_core

PRESENCE_ON_MS = 6_000
PRESENCE_OFF_MS = 8_000
PROBE_MIN_WAIT_MS = 2_000
PROBE_MAX_WAIT_MS = 180_000
PROBE_BUSY_MS = 90_000
MAX_MICS = 64
MAX_FRAME_MS = 1_000
U32 = 2 ** 32


@dataclass(frozen=True, slots=True)
class RoomStep:
    playing: bool
    change: str
    probe: bool


class _Presence:
    __slots__ = ("heard", "quiet", "playing")

    def __init__(self) -> None:
        self.heard = 0
        self.quiet = 0
        self.playing = False

    def feed(self, music: bool, frame_ms: int) -> str:
        frame = max(1, min(MAX_FRAME_MS, int(frame_ms)))
        if music:
            self.heard = min(self.heard + frame, PRESENCE_ON_MS * 2)
            self.quiet = 0
        else:
            self.heard = max(0, self.heard - frame // 2)
            self.quiet = min(self.quiet + frame, PRESENCE_OFF_MS * 2)
        if not self.playing and self.heard >= PRESENCE_ON_MS:
            self.playing = True
            return "started"
        if self.playing and self.quiet >= PRESENCE_OFF_MS:
            self.playing = False
            self.heard = 0
            return "stopped"
        return ""


class PyMusicRoom:

    def __init__(self) -> None:
        self.mics: dict[int, _Presence] = {}
        self.next_ms = 0
        self.busy_since: int | None = None
        self.is_playing = False
        self.next_id = 0

    def join(self) -> int | None:
        if len(self.mics) >= MAX_MICS:
            return None
        mic, self.next_id = self.next_id, (self.next_id + 1) % U32
        self.mics[mic] = _Presence()
        return mic

    def leave(self, mic: int) -> str:
        self.mics.pop(mic, None)
        return self._settle()

    def _settle(self) -> str:
        anyone = any(p.playing for p in self.mics.values())
        change = "started" if anyone and not self.is_playing else "stopped" if self.is_playing and not anyone else ""
        self.is_playing = anyone
        return change

    def _busy(self, now_ms: int) -> bool:
        return self.busy_since is not None and now_ms - self.busy_since < PROBE_BUSY_MS

    def feed(self, mic: int, music: bool, idle: bool, frame_ms: int, now_ms: int) -> tuple[bool, str, bool]:
        presence = self.mics.get(mic)
        if presence is None:
            return self.is_playing, "", False
        mine = presence.feed(music, frame_ms)
        change = self._settle()
        if "started" in (change, mine):
            self.next_ms = min(self.next_ms, now_ms)
        probe = bool(idle and presence.playing and not self._busy(now_ms) and now_ms >= self.next_ms)
        if probe:
            self.busy_since = now_ms
        return self.is_playing, change, probe

    def finish(self, now_ms: int, wait_ms: int) -> None:
        self.busy_since = None
        self.next_ms = now_ms + max(PROBE_MIN_WAIT_MS, min(PROBE_MAX_WAIT_MS, int(wait_ms)))

    def playing(self) -> bool:
        return self.is_playing

    def mic_playing(self, mic: int) -> bool:
        presence = self.mics.get(mic)
        return bool(presence and presence.playing)


class MusicRoom:

    def __init__(self, engine=None) -> None:
        if engine is None:
            native = native_core.symbol("RustMusicRoom")
            if native is None:
                native_core.python_fallback("ear.music")
            engine = native() if native is not None else PyMusicRoom()
        self.engine = engine

    def join(self) -> int | None:
        return self.engine.join()

    def leave(self, mic: int | None) -> str:
        return self.engine.leave(mic) if mic is not None else ""

    def feed(self, mic: int | None, music: bool, idle: bool, frame_ms: int, now: float) -> RoomStep:
        if mic is None:
            return RoomStep(self.engine.playing(), "", False)
        playing, change, probe = self.engine.feed(mic, bool(music), bool(idle), int(frame_ms), max(0, int(now * 1000)))
        return RoomStep(bool(playing), str(change), bool(probe))

    def finish(self, now: float, wait_seconds: float) -> None:
        self.engine.finish(max(0, int(now * 1000)), max(0, int(wait_seconds * 1000)))

    @property
    def playing(self) -> bool:
        return bool(self.engine.playing())


ROOM = MusicRoom()
