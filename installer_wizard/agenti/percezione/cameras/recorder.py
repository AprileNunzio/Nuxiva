import asyncio
import collections
import shutil
import subprocess
import time

from agenti.cameras.cameras import CAM_DIR, cameras
from agenti.cameras.segments import SegmentError, strip_audio, video_args
from agenti.nvr.archive import archive
from state import store

SEGMENT_SECONDS = 60
STRIP_RETRIES = 3


def _source_args(cam: dict) -> list:
    if cam["kind"] == "webcam":
        dev = cam["url"] or "0"
        return ["-f", "v4l2", "-i", dev if dev.startswith("/dev/") else f"/dev/video{dev}"]
    return ["-rtsp_transport", "tcp", "-i", cam["url"]] if cam["url"].lower().startswith(("rtsp://", "rtsps://")) \
        else ["-i", cam["url"]]


def _nvr_settings() -> dict:
    from agenti.nvr.service import nvr
    return nvr.settings


class Recorder:
    def __init__(self) -> None:
        self.procs: dict = {}
        self.audio: dict[str, dict] = {}
        self.failures: dict[str, int] = {}
        self.last_exit: dict[str, str] = {}
        self.watchers: set = set()

    def _audio_ok(self, cam: dict) -> bool:
        return bool(self.audio.get(cam["id"], {}).get("allowed"))

    def _refresh_audio(self, wanted: dict) -> None:
        from agenti.nvr.notice import notice
        from agenti.nvr.privacy import camera_audio
        settings = _nvr_settings()
        rows = [camera_audio(c, settings) for c in wanted.values()]
        self.audio = {r["camera"]: r for r in rows}
        notice.tick(rows, settings)

    async def _start(self, cam: dict) -> None:
        incoming = CAM_DIR / cam["id"] / "incoming"
        incoming.mkdir(parents=True, exist_ok=True)
        args = ["ffmpeg", "-loglevel", "error", "-nostdin", *_source_args(cam),
                *video_args(cam), *(["-c:a", "aac"] if self._audio_ok(cam) else ["-an"]), "-f", "segment", "-segment_time", str(SEGMENT_SECONDS),
                "-reset_timestamps", "1", "-segment_format_options", "movflags=+faststart", "-strftime", "1", str(incoming / "seg_%Y%m%d_%H%M%S.mp4")]
        try:
            proc = await asyncio.create_subprocess_exec(*args, stdout=asyncio.subprocess.DEVNULL,
                                                        stderr=asyncio.subprocess.PIPE)
        except OSError as exc:
            store.event("WARN", f"Telecamera {cam['name']}: avvio registrazione non riuscito ({exc})", "cameras")
            return
        self.procs[cam["id"]] = {"proc": proc, "sig": self._sig_of(cam)}
        task = asyncio.create_task(self._watch(cam, proc))
        self.watchers.add(task)
        task.add_done_callback(self.watchers.discard)
        mode = "audio+video" if self._audio_ok(cam) else "solo video"
        store.event("INFO", f"Registrazione cifrata avviata: {cam['name']} ({mode}, anello {cam['retention_min']} min)", "cameras")

    async def _watch(self, cam: dict, proc) -> None:
        tail: collections.deque = collections.deque(maxlen=4)
        while line := await proc.stderr.readline():
            text = line.decode("utf-8", "replace").strip()
            if text:
                tail.append("".join(ch if ch.isprintable() else " " for ch in text)[:200])
        code = await proc.wait()
        if code in (0, -15, 255) and not tail:
            return
        reason = tail[-1] if tail else f"exit {code}"
        if self.last_exit.get(cam["id"]) != reason:
            self.last_exit[cam["id"]] = reason
            store.event("WARN", f"Telecamera {cam['name']}: registrazione interrotta (recorder_exit {code}: {reason})", "cameras")

    def _stop(self, cid: str) -> None:
        rec = self.procs.pop(cid, None)
        if rec and rec["proc"].returncode is None:
            try:
                rec["proc"].terminate()
            except ProcessLookupError:
                pass

    @staticmethod
    def _sig(cam: dict) -> str:
        return f"{cam['kind']}|{cam['url']}|{cam['retention_min']}"

    def _sig_of(self, cam: dict) -> str:
        return f"{self._sig(cam)}|{int(self._audio_ok(cam))}"

    def _encrypt_pending(self, cam: dict) -> None:
        incoming = CAM_DIR / cam["id"] / "incoming"
        if not incoming.exists():
            return
        rec = self.procs.get(cam["id"])
        segments = sorted(incoming.glob("seg_*.mp4"))
        if rec and rec["proc"].returncode is None and segments:
            segments = segments[:-1]
        now = time.time()
        for seg in segments:
            try:
                if now - seg.stat().st_mtime >= 3:
                    self._archive_one(cam, seg)
            except SegmentError as exc:
                self._segment_failed(cam, seg, exc)
            except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as exc:
                store.event("WARN", f"Telecamera {cam['name']}: segmento non archiviato ({type(exc).__name__}: {exc})", "cameras")

    def _archive_one(self, cam: dict, seg) -> None:
        allowed = self._audio_ok(cam)
        if not allowed:
            strip_audio(seg)
        archive.ingest(cam["id"], seg, tier="continuous", audio_allowed=allowed)
        self.failures.pop(str(seg), None)

    def _segment_failed(self, cam: dict, seg, exc: SegmentError) -> None:
        key = str(seg)
        count = self.failures.get(key, 0) + 1
        self.failures[key] = count
        if exc.discard or count >= STRIP_RETRIES:
            seg.unlink(missing_ok=True)
            self.failures.pop(key, None)
            store.event("WARN", f"Telecamera {cam['name']}: segmento {seg.name} scartato ({exc})", "cameras")
        elif count == 1:
            store.event("WARN", f"Telecamera {cam['name']}: segmento {seg.name} non archiviato, nuovo tentativo ({exc})", "cameras")

    def _maintain(self, wanted: dict) -> None:
        if not archive.due():
            return
        from agenti.nvr.service import nvr
        events = nvr.store.camera_times(time.time() - int(nvr.settings.get("retention_days", 30)) * 86400)
        archive.maintain(events, nvr.settings, wanted)

    def _prune(self, cam: dict) -> None:
        folder = CAM_DIR / cam["id"]
        if not folder.exists():
            return
        cutoff = time.time() - cam["retention_min"] * 60 - SEGMENT_SECONDS
        for seg in folder.glob("seg_*.mp4"):
            try:
                if seg.stat().st_mtime < cutoff:
                    seg.unlink(missing_ok=True)
            except OSError:
                pass

    def _enroll_connected_cameras(self) -> None:
        try:
            from agenti.vision.webcams import webcams
            devices = webcams.state.get("devices") or []
            for dev in devices:
                node = dev.get("rgb") or dev.get("ir")
                if not node:
                    continue
                exists = any(c.get("url") == node or c.get("node") == node for c in cameras.items.values())
                if not exists:
                    name = str(dev.get("name") or "Webcam").strip()[:40]
                    cameras.add({"name": name, "kind": "webcam", "url": node, "node": node,
                                 "retention_min": 60, "enabled": True, "record": True, "consent": True})
        except Exception:
            pass

    async def run(self) -> None:
        if not shutil.which("ffmpeg"):
            return
        while True:
            try:
                self._enroll_connected_cameras()
                wanted = {c["id"]: c for c in cameras.items.values() if cameras._recording(c)}
                self._refresh_audio(wanted)
                for cid in list(self.procs):
                    rec = self.procs[cid]
                    if cid not in wanted or rec["sig"] != self._sig_of(wanted[cid]) or rec["proc"].returncode is not None:
                        self._stop(cid)
                for cid, cam in wanted.items():
                    if cid not in self.procs:
                        await self._start(cam)
                    self._encrypt_pending(cam)
                    self._prune(cam)
                await asyncio.to_thread(self._maintain, wanted)
            except Exception as exc:
                store.event("WARN", f"Registratore telecamere: {exc}", "cameras")
            await asyncio.sleep(15)


recorder = Recorder()
