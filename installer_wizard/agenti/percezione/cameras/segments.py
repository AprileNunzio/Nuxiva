import functools
import json
import shutil
import subprocess
from pathlib import Path

PROBE_TIMEOUT = 15
STRIP_TIMEOUT = 120
DETAIL_MAX = 160
DISCARD_CODES = frozenset({"segment_empty", "segment_unreadable", "segment_no_video"})


class SegmentError(RuntimeError):
    def __init__(self, code: str, detail: str = "") -> None:
        self.code = code
        self.detail = detail
        super().__init__(f"{code}: {detail}" if detail else code)

    @property
    def discard(self) -> bool:
        return self.code in DISCARD_CODES


def _tail(raw: bytes | str | None) -> str:
    text = raw.decode("utf-8", "replace") if isinstance(raw, bytes) else (raw or "")
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    if not lines:
        return ""
    clean = "".join(ch if ch.isprintable() else " " for ch in lines[-1])
    return clean[:DETAIL_MAX]


def _exe(name: str) -> str:
    exe = shutil.which(name)
    if not exe:
        raise SegmentError(f"{name}_missing")
    return exe


def streams(path: Path) -> set[str]:
    try:
        size = path.stat().st_size
    except FileNotFoundError as exc:
        raise SegmentError("segment_missing", path.name) from exc
    if size == 0:
        raise SegmentError("segment_empty", path.name)
    try:
        done = subprocess.run([_exe("ffprobe"), "-v", "error", "-print_format", "json", "-show_entries", "stream=codec_type",
                               str(path)], capture_output=True, timeout=PROBE_TIMEOUT, check=False)
    except subprocess.TimeoutExpired as exc:
        raise SegmentError("segment_probe_timeout", path.name) from exc
    if done.returncode != 0:
        raise SegmentError("segment_unreadable", _tail(done.stderr) or f"ffprobe exit {done.returncode}")
    try:
        data = json.loads(done.stdout or b"{}")
    except ValueError as exc:
        raise SegmentError("segment_unreadable", "ffprobe json") from exc
    kinds = {s.get("codec_type") for s in data.get("streams") or [] if isinstance(s, dict)}
    if "video" not in kinds:
        raise SegmentError("segment_no_video", path.name)
    return {k for k in kinds if isinstance(k, str)}


def strip_audio(path: Path) -> bool:
    if "audio" not in streams(path):
        return False
    tmp = path.with_name(path.stem + ".strip.tmp")
    try:
        done = subprocess.run([_exe("ffmpeg"), "-nostdin", "-loglevel", "error", "-y", "-i", str(path), "-map", "0:v", "-c", "copy",
                               "-movflags", "+faststart", "-f", "mp4", str(tmp)], capture_output=True, timeout=STRIP_TIMEOUT, check=False)
    except subprocess.TimeoutExpired as exc:
        tmp.unlink(missing_ok=True)
        raise SegmentError("audio_strip_timeout", path.name) from exc
    if done.returncode != 0 or not tmp.exists() or tmp.stat().st_size == 0:
        tmp.unlink(missing_ok=True)
        raise SegmentError("audio_strip_failed", _tail(done.stderr) or f"ffmpeg exit {done.returncode}")
    tmp.replace(path)
    return True


@functools.cache
def _encoders() -> frozenset[str]:
    exe = shutil.which("ffmpeg")
    if not exe:
        return frozenset()
    try:
        done = subprocess.run([exe, "-hide_banner", "-encoders"], capture_output=True, text=True, timeout=PROBE_TIMEOUT, check=False)
    except (OSError, subprocess.SubprocessError):
        return frozenset()
    names = set()
    for line in done.stdout.splitlines():
        parts = line.split()
        if len(parts) >= 2 and parts[0].startswith("V"):
            names.add(parts[1])
    return frozenset(names)


def video_args(cam: dict) -> list[str]:
    if cam.get("kind") != "webcam":
        return ["-c:v", "copy"]
    if "libx264" in _encoders():
        return ["-c:v", "libx264", "-preset", "veryfast", "-tune", "zerolatency", "-pix_fmt", "yuv420p", "-g", "50"]
    return ["-c:v", "mpeg4", "-q:v", "5", "-pix_fmt", "yuv420p"]
