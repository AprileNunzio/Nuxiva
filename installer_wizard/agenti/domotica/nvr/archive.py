import json
import logging
import shutil
import subprocess
import threading
import time
from pathlib import Path

from agenti.nvr import settings as nvr_settings
from agenti.nvr.catalog import Catalog
from agenti.nvr.vault import DEFAULT_DURATION_MS, MediaVault, VaultError, clean_id, media_vault, stamp_ms

log = logging.getLogger("nuxiva.nvr.archive")
PROBE_TIMEOUT = 15
EVENT_PAD_MS = 30_000
SAVE_EVERY = 60.0
MAINTAIN_EVERY = 300.0


def probe(path: Path) -> dict:
    exe = shutil.which("ffprobe")
    fallback = {"duration_ms": DEFAULT_DURATION_MS, "audio": True, "video": True}
    if not exe:
        return fallback
    try:
        done = subprocess.run([exe, "-v", "error", "-print_format", "json", "-show_entries",
                               "format=duration:stream=codec_type", str(path)],
                              capture_output=True, timeout=PROBE_TIMEOUT, check=False)
        data = json.loads(done.stdout or b"{}")
    except (OSError, subprocess.SubprocessError, ValueError) as exc:
        log.debug("NVR: ffprobe non riuscito su %s: %s", path.name, exc)
        return fallback
    kinds = {s.get("codec_type") for s in data.get("streams") or [] if isinstance(s, dict)}
    try:
        seconds = float((data.get("format") or {}).get("duration") or 0)
    except (TypeError, ValueError):
        seconds = 0.0
    if not kinds:
        return fallback
    return {"duration_ms": int(seconds * 1000) if 0 < seconds < 3600 else DEFAULT_DURATION_MS,
            "audio": "audio" in kinds, "video": "video" in kinds}


class NvrArchive:
    def __init__(self, vault: MediaVault | None = None) -> None:
        self.vault = vault or media_vault
        self.catalog = Catalog(self.vault)
        self.lock = threading.Lock()
        self.last_save = 0.0
        self.last_maintain = 0.0

    def ingest(self, camera_id: str, raw_path: Path, tier: str = "continuous", audio_allowed: bool = True) -> dict:
        camera_id = clean_id(camera_id)
        meta = probe(raw_path)
        start_ms = stamp_ms(raw_path.name, raw_path.stat().st_mtime)
        out = self.vault.encrypt_file(camera_id, raw_path, tier=tier, has_audio=meta["audio"] and audio_allowed,
                                      has_video=meta["video"], recorded_at_ms=start_ms, duration_ms=meta["duration_ms"])
        row = self.catalog.row_from_header(out)
        if row is None:
            raise VaultError("nvr.segment.unreadable")
        self.catalog.add(row)
        self.save_soon()
        return row

    def save_soon(self, force: bool = False) -> None:
        now = time.monotonic()
        if force or now - self.last_save >= SAVE_EVERY:
            self.last_save = now
            self.catalog.save()

    def policy(self, settings: dict | None = None, cameras: dict | None = None) -> dict:
        cfg = settings or nvr_settings.load()
        overrides = {}
        for cid, cam in (cameras or {}).items():
            minutes = int(cam.get("retention_min") or 0)
            if minutes > 0:
                overrides[cid] = minutes * 60_000
        return {"continuous_ms": int(cfg.get("continuous_hours", 48)) * 3_600_000,
                "event_ms": int(cfg.get("retention_days", 30)) * 86_400_000,
                "quota_bytes": self.vault.quota_bytes(cfg.get("storage_percent", 20), cfg.get("storage_max_gb", 0)),
                "event_pad_ms": EVENT_PAD_MS, "continuous_overrides": overrides}

    def maintain(self, events: list[tuple[str, int]], settings: dict | None = None, cameras: dict | None = None,
                 now_ms: int | None = None) -> dict:
        with self.lock:
            now_ms = now_ms or int(time.time() * 1000)
            plan = self.catalog.plan(self.policy(settings, cameras), events, now_ms)
            for camera, segment_id in plan["promote"]:
                self.catalog.set_tier(camera, segment_id, "event")
            removed = 0
            for camera, segment_id in plan["expire"] + plan["evict"]:
                self.vault.delete(camera, segment_id)
                self.catalog.remove(camera, segment_id)
                removed += 1
            self.last_maintain = time.monotonic()
            self.save_soon(force=True)
            return {"promoted": len(plan["promote"]), "expired": len(plan["expire"]), "evicted": len(plan["evict"]),
                    "removed": removed, "kept_bytes": plan["kept_bytes"]}

    def due(self) -> bool:
        return time.monotonic() - self.last_maintain >= MAINTAIN_EVERY

    def pin(self, camera_id: str, segment_id: str, pinned: bool) -> dict:
        row = self.catalog.get(clean_id(camera_id), clean_id(segment_id))
        if row is None:
            raise VaultError("nvr.segment.not_found")
        self.catalog.set_tier(camera_id, segment_id, "pinned" if pinned else "event")
        self.save_soon(force=True)
        return self.catalog.get(camera_id, segment_id)

    def delete(self, camera_id: str, segment_id: str) -> bool:
        gone = self.vault.delete(camera_id, segment_id)
        gone = self.catalog.remove(clean_id(camera_id), clean_id(segment_id)) is not None or gone
        self.save_soon(force=True)
        return gone


archive = NvrArchive()
