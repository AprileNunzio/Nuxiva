import hashlib
import logging
import threading
import time
from collections.abc import Callable

import native_core
import numpy as np
from capture_cadence import SOURCES, make
from capture_embed import TileEmbedder, thumb
from capture_sources import active_window, grab_screen

log = logging.getLogger("nuxiva.vision.capture")

TICK_S = 0.5
MAX_ERRORS = 1000
SCENE_PREFIX = "scene-"


def scene_ref(context: list[float] | None) -> str | None:
    if not context:
        return None
    quantized = bytes(max(0, min(255, int((x + 1.0) * 127.5))) for x in context[:256])
    return SCENE_PREFIX + hashlib.sha256(quantized).hexdigest()[:20]


class CaptureDaemon:
    def __init__(self, settings: Callable[[str, str], str], webcam: Callable[[], np.ndarray | None],
                 embedder=None, screen: Callable[[], np.ndarray | None] = grab_screen,
                 window: Callable[[], tuple[str, str] | None] = active_window,
                 clock: Callable[[], float] = time.time) -> None:
        self._cfg = settings
        self._webcam = webcam
        self._screen = screen
        self._window = window
        self._clock = clock
        self.embedder = embedder or TileEmbedder()
        self.cadence = make(self._ms("NUXIVA_CAPTURE_INTERVAL", 2000), self._ms("NUXIVA_CAPTURE_CEILING", 30_000))
        cls = native_core.symbol("RustVisualBuffer")
        self.buffer = None if cls is None else cls(False, self._ms("NUXIVA_CAPTURE_INTERVAL", 2000), 300_000, 256)
        self.stats = {"embedded": 0, "unchanged": 0, "rejected": 0, "errors": 0, "no_embedding": 0}
        self.reasons: dict[str, int] = {}
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def _ms(self, key: str, default: int) -> int:
        try:
            return max(250, int(float(self._cfg(key, str(default)))))
        except (TypeError, ValueError):
            return default

    def consent(self) -> bool:
        return self._cfg("NUXIVA_CAPTURE_CONSENT", "0") == "1"

    def _lanes(self) -> list[str]:
        raw = self._cfg("NUXIVA_CAPTURE_SOURCES", "screen,webcam")
        return [s for s in SOURCES if s in {p.strip() for p in raw.split(",")}]

    def _frame(self, source: str) -> tuple[np.ndarray, str, str] | None:
        if source == "webcam":
            image = self._webcam()
            return None if image is None else (image, "webcam", "")
        info = self._window()
        if info is None:
            self._count("window_unknown")
            return None
        if self.buffer.screens(info[0], info[1]):
            self._count("sensitive")
            return None
        image = self._screen()
        if image is None:
            return None
        if self._window() != info:
            self._count("window_changed")
            return None
        return image, info[0], info[1]

    def _count(self, reason: str) -> None:
        if len(self.reasons) < 32 or reason in self.reasons:
            self.reasons[reason] = self.reasons.get(reason, 0) + 1

    def step(self, now: float | None = None) -> int:
        if self.buffer is None:
            return 0
        moment = self._clock() if now is None else now
        now_ms = int(moment * 1000)
        interval = self._ms("NUXIVA_CAPTURE_INTERVAL", 2000)
        self.buffer.set_policy(self.consent(), interval, 300_000, 256)
        if not self.consent():
            return 0
        stored = 0
        for source in self._lanes():
            if not self.cadence.due(source, now_ms):
                continue
            grabbed = self._frame(source)
            if grabbed is None:
                continue
            image, app, title = grabbed
            stored += self._admit(source, image, app, title, now_ms)
        self.buffer.expire(now_ms)
        return stored

    def _admit(self, source: str, image: np.ndarray, app: str, title: str, now_ms: int) -> int:
        try:
            verdict = self.cadence.admit(source, thumb(image), now_ms)
        except ValueError:
            self.stats["errors"] = min(MAX_ERRORS, self.stats["errors"] + 1)
            return 0
        if verdict != "embed":
            self.stats["unchanged"] += verdict == "unchanged"
            return 0
        vector = self.embedder.embed(image)
        if not vector:
            self.stats["no_embedding"] += 1
            return 0
        outcome = self.buffer.push(source, app, title, now_ms, vector)
        if outcome == "stored":
            self.stats["embedded"] += 1
            return 1
        self.stats["rejected"] += 1
        self._count(outcome)
        return 0

    def view(self, now: float | None = None) -> dict:
        moment = self._clock() if now is None else now
        now_ms = int(moment * 1000)
        if self.buffer is None:
            return {"available": False, "active": False}
        active, source, frames, last_ms = self.buffer.indicator(now_ms)
        return {"available": True, "consent": self.consent(), "active": active, "source": source, "frames": frames,
                "last_ms": last_ms, "app": self.buffer.current_app(now_ms), "scene": scene_ref(self.buffer.context(now_ms)),
                "embedder": self.embedder.name, "stats": dict(self.stats), "rejections": dict(self.reasons)}

    def query(self, probe: list[float], k: int = 5) -> list[dict]:
        if self.buffer is None:
            return []
        hits = self.buffer.query(probe, int(self._clock() * 1000), k)
        return [{"app": a, "source": s, "at_ms": t, "score": round(float(sc), 4)} for a, s, t, sc in hits]

    def wipe(self) -> None:
        if self.buffer is not None:
            self.buffer.wipe()
        self.cadence.reset()

    def start(self) -> None:
        if self._thread is not None or self.buffer is None:
            return
        self._thread = threading.Thread(target=self._loop, daemon=True, name="cattura-visiva")
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        self.wipe()

    def _loop(self) -> None:
        while not self._stop.wait(TICK_S):
            try:
                self.step()
            except (OSError, ValueError, RuntimeError) as exc:
                self.stats["errors"] = min(MAX_ERRORS, self.stats["errors"] + 1)
                log.error("Ciclo di cattura visiva non riuscito: %s", exc)


def embedder_from(cfg: Callable[[str, str], str]):
    from capture_embed import VlmEmbedder
    if cfg("NUXIVA_CAPTURE_EMBEDDER", "tile") != "vlm":
        return TileEmbedder()
    try:
        return VlmEmbedder(cfg("NUXIVA_CAPTURE_OLLAMA_URL", "http://127.0.0.1:11434"), cfg("NUXIVA_CAPTURE_VLM_MODEL", ""),
                           cfg("NUXIVA_CAPTURE_EMBED_MODEL", ""))
    except ValueError as exc:
        log.error("Embedder visivo non valido, uso quello a tessere: %s", exc)
        return TileEmbedder()
