import asyncio
import shutil
import time

from features.cameras.cameras import CAM_DIR, cameras
from features.nvr.vault import media_vault
from state import store

SEGMENT_SECONDS = 60


def _source_args(cam: dict) -> list:
    if cam["kind"] == "webcam":
        dev = cam["url"] or "0"
        return ["-f", "v4l2", "-i", dev if dev.startswith("/dev/") else f"/dev/video{dev}"]
    return ["-rtsp_transport", "tcp", "-i", cam["url"]] if cam["url"].lower().startswith(("rtsp://", "rtsps://")) \
        else ["-i", cam["url"]]


class Recorder:
    def __init__(self) -> None:
        self.procs: dict = {}

    async def _start(self, cam: dict) -> None:
        incoming = CAM_DIR / cam["id"] / "incoming"
        incoming.mkdir(parents=True, exist_ok=True)
        args = ["ffmpeg", "-loglevel", "error", "-nostdin", *_source_args(cam),
                "-c:v", "copy", "-c:a", "aac", "-f", "segment", "-segment_time", str(SEGMENT_SECONDS),
                "-reset_timestamps", "1", "-strftime", "1", str(incoming / "seg_%Y%m%d_%H%M%S.mp4")]
        try:
            proc = await asyncio.create_subprocess_exec(*args, stdout=asyncio.subprocess.DEVNULL,
                                                        stderr=asyncio.subprocess.DEVNULL)
        except OSError as exc:
            store.event("WARN", f"Telecamera {cam['name']}: avvio registrazione non riuscito ({exc})", "cameras")
            return
        self.procs[cam["id"]] = {"proc": proc, "sig": self._sig(cam)}
        store.event("INFO", f"Registrazione cifrata avviata: {cam['name']} (audio+video, anello {cam['retention_min']} min)", "cameras")

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

    def _encrypt_pending(self, cam: dict) -> None:
        incoming = CAM_DIR / cam["id"] / "incoming"
        if not incoming.exists():
            return
        now = time.time()
        for seg in sorted(incoming.glob("seg_*.mp4")):
            try:
                if now - seg.stat().st_mtime >= 3:
                    media_vault.encrypt_file(cam["id"], seg, tier="continuous")
            except OSError:
                pass

    def _prune(self, cam: dict) -> None:
        media_vault.prune(cam["id"])
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

    async def run(self) -> None:
        if not shutil.which("ffmpeg"):
            return
        while True:
            try:
                wanted = {c["id"]: c for c in cameras.items.values() if cameras._recording(c)}
                for cid in list(self.procs):
                    rec = self.procs[cid]
                    if cid not in wanted or rec["sig"] != self._sig(wanted[cid]) or rec["proc"].returncode is not None:
                        self._stop(cid)
                for cid, cam in wanted.items():
                    if cid not in self.procs:
                        await self._start(cam)
                    self._encrypt_pending(cam)
                    self._prune(cam)
            except Exception as exc:
                store.event("WARN", f"Registratore telecamere: {exc}", "cameras")
            await asyncio.sleep(15)


recorder = Recorder()
