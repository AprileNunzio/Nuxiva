import asyncio
import logging
import shutil
import subprocess
import time

from agenti.ear import scribe_spool
from agenti.nvr.transcripts import TranscriptStore, store as transcript_store

log = logging.getLogger("nuxiva.nvr.scribe")
LOOP_S = 20.0
MAX_PENDING = 8
LOOKBACK_MS = 48 * 3_600_000
FFMPEG_TIMEOUT = 120
RATE = 16000


def extract_pcm(media: bytes) -> bytes:
    exe = shutil.which("ffmpeg")
    if not exe:
        raise RuntimeError("nvr.scribe.ffmpeg_missing")
    done = subprocess.run([exe, "-nostdin", "-loglevel", "error", "-i", "pipe:0", "-vn", "-ac", "1", "-ar", str(RATE),
                           "-f", "s16le", "pipe:1"], input=media, capture_output=True, timeout=FFMPEG_TIMEOUT, check=False)
    if done.returncode != 0:
        raise RuntimeError("nvr.scribe.decode_failed")
    return done.stdout


def voice_allowed(slug: str | None) -> bool:
    if not slug:
        return False
    try:
        from agenti.sentinel import memory_people
    except ImportError:
        return False
    return memory_people.allows_voice(memory_people._profile(slug))


class ScribeDispatcher:
    def __init__(self, archive=None, store: TranscriptStore | None = None, extract=extract_pcm,
                 allowed=voice_allowed) -> None:
        if archive is None:
            from agenti.nvr.archive import archive as default_archive
            archive = default_archive
        self.archive = archive
        self.store = store or transcript_store
        self.extract = extract
        self.allowed = allowed
        self.failed: set[str] = set()

    def candidates(self, now_ms: int) -> list[dict]:
        rows = []
        for cam in self.archive.catalog.summary():
            for seg in self.archive.catalog.range(cam["camera"], now_ms - LOOKBACK_MS, now_ms, 5000):
                if seg["audio"] and not self.store.exists(seg["camera"], seg["id"]):
                    rows.append(seg)
        return sorted(rows, key=lambda s: s["start_ms"], reverse=True)

    def enqueue(self, now_ms: int | None = None) -> int:
        queued = set(scribe_spool.names("jobs")) | set(scribe_spool.names("done"))
        room = MAX_PENDING - len(queued)
        added = 0
        for seg in self.candidates(now_ms or int(time.time() * 1000)):
            if room <= 0:
                break
            name = scribe_spool.job_name(seg["camera"], seg["id"])
            if name in queued or name in self.failed:
                continue
            try:
                path = self.archive.vault.path_for(seg["camera"], seg["id"])
                pcm = self.extract(self.archive.vault.decrypt_file(seg["camera"], path))
                scribe_spool.put("jobs", name, {"camera": seg["camera"], "segment": seg["id"],
                                                "start_ms": seg["start_ms"]}, pcm)
            except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as exc:
                log.warning("NVR: audio di %s non preparato per la trascrizione: %s", name, exc)
                self.failed.add(name)
                continue
            room -= 1
            added += 1
        return added

    def collect(self) -> int:
        saved = 0
        for name in scribe_spool.names("done"):
            try:
                header, _ = scribe_spool.take("done", name)
                camera, segment = name.split("__", 1)
                if header.get("camera") != camera or header.get("segment") != segment:
                    raise ValueError("nvr.scribe.mismatch")
                start = int(header.get("start_ms") or 0)
                turns = []
                for t in header.get("turns") or []:
                    slug = t.get("speaker") if self.allowed(t.get("speaker")) else None
                    turns.append({"start_ms": start + int(t["start_ms"]), "end_ms": start + int(t["end_ms"]),
                                  "text": str(t["text"])[:4000], "speaker": slug,
                                  "speaker_score": float(t.get("speaker_score") or 0.0) if slug else 0.0,
                                  "voice": None if slug else (str(t.get("voice") or "")[:20] or None)})
                self.store.save(camera, segment, {"camera": camera, "segment": segment, "start_ms": start,
                                                  "seconds": header.get("seconds"), "turns": turns,
                                                  "at": int(time.time() * 1000)})
                self._observe(camera, turns)
                saved += 1
            except (OSError, ValueError, KeyError, TypeError, scribe_spool.SpoolError) as exc:
                log.warning("NVR: risultato di trascrizione %s scartato: %s", name, exc)
        return saved

    def _observe(self, camera: str, turns: list[dict]) -> None:
        try:
            from agenti.rescue.detector import detect_speech_intent
            from agenti.rescue.coordinator import coordinator
        except ImportError:
            return
        for t in turns:
            kind, conf = detect_speech_intent(t["text"])
            if kind:
                coordinator.observe(kind, 0.9, conf, f"nvr:{camera}")

    async def run(self, enabled) -> None:
        while True:
            await asyncio.sleep(LOOP_S)
            try:
                await asyncio.to_thread(self.collect)
                if enabled():
                    await asyncio.to_thread(self.enqueue)
            except (OSError, ValueError, RuntimeError) as exc:
                log.warning("NVR: ciclo di trascrizione: %s", exc)


dispatcher = None


def get_dispatcher() -> ScribeDispatcher:
    global dispatcher
    if dispatcher is None:
        dispatcher = ScribeDispatcher()
    return dispatcher
