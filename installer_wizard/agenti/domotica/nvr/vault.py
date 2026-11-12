import json
import logging
import os
import re
import secrets
import shutil
import time
from datetime import datetime
from pathlib import Path
from typing import Iterator

from config import STATE_DIR
from agenti.nvr import legacy, nvm2
from agenti.sentinel import vault as sentinel_vault
from agenti.sentinel.record import NUXIVA, record
import native_module

log = logging.getLogger("nuxiva.nvr.vault")
CHUNK_SIZE = nvm2.CHUNK_SIZE
VAULT_DIR = STATE_DIR / "cameras" / "vault"
ID = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
STAMP = re.compile(r"(\d{8}_\d{6})")
DEFAULT_DURATION_MS = 60000
AUDIT_EVERY = 300.0
MAX_SEGMENT_BYTES = 2 * 1024 * 1024 * 1024


class VaultError(ValueError):
    pass


def day_str(ts: float | None = None) -> str:
    return datetime.fromtimestamp(ts if ts is not None else time.time()).strftime("%Y-%m-%d")


def clean_id(value: str) -> str:
    text = str(value or "")
    if not ID.match(text):
        raise VaultError("nvr.id.invalid")
    return text


def stamp_ms(name: str, fallback: float) -> int:
    found = STAMP.search(name)
    if found:
        try:
            return int(datetime.strptime(found.group(1), "%Y%m%d_%H%M%S").timestamp() * 1000)
        except ValueError:
            pass
    return int(fallback * 1000)


def _private_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{secrets.token_hex(6)}.tmp")
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, path)
    finally:
        tmp.unlink(missing_ok=True)


class MediaVault:
    def __init__(self, continuous_seconds: int = 7200, event_seconds: int = 604800) -> None:
        self.continuous_seconds = continuous_seconds
        self.event_seconds = event_seconds
        self.root = VAULT_DIR
        self._audited: dict[tuple, float] = {}

    def _master_key(self) -> bytes:
        try:
            return sentinel_vault.secret("media")
        except (OSError, sentinel_vault.VaultError) as exc:
            log.warning("NVR: chiave media della Sentinella non disponibile, uso la chiave locale: %s", exc)
        path = self.root / ".master.key"
        if not path.exists():
            _private_write(path, secrets.token_bytes(32))
        key = path.read_bytes()
        if len(key) != 32:
            raise VaultError("nvr.key.invalid")
        return key

    def _engine(self):
        cls = native_module.feature("RustMediaVault")
        if cls is None or not hasattr(cls, "seal_v2"):
            native_module.python_fallback("nvr.vault")
            return None
        return cls(self._master_key(), self.continuous_seconds, self.event_seconds)

    def path_for(self, camera_id: str, segment_id: str) -> Path:
        return self.root / clean_id(camera_id) / f"{clean_id(segment_id)}.nvm"

    def seal(self, camera_id: str, segment_id: str, raw: bytes, *, recorded_at_ms: int, duration_ms: int,
             tier: str = "continuous", has_audio: bool = True, has_video: bool = True, nonce: bytes | None = None) -> bytes:
        nonce = nonce or secrets.token_bytes(nvm2.NONCE_LEN)
        day = day_str(recorded_at_ms / 1000)
        args = (clean_id(camera_id), day, clean_id(segment_id), int(recorded_at_ms), int(duration_ms),
                bool(has_audio), bool(has_video), tier, nonce, raw)
        engine = self._engine()
        if engine is not None:
            return bytes(engine.seal_v2(*args))
        return nvm2.py_seal(self._master_key(), *args)

    def encrypt_file(self, camera_id: str, raw_path: Path, tier: str = "continuous", has_audio: bool = True,
                     has_video: bool = True, recorded_at_ms: int | None = None, duration_ms: int | None = None) -> Path:
        stat = raw_path.stat()
        if stat.st_size > MAX_SEGMENT_BYTES:
            raise VaultError("nvr.segment.too_large")
        raw = raw_path.read_bytes()
        segment_id = clean_id(raw_path.stem)
        start_ms = recorded_at_ms if recorded_at_ms is not None else stamp_ms(raw_path.name, stat.st_mtime)
        out = self.path_for(camera_id, segment_id)
        sealed = self.seal(camera_id, segment_id, raw, recorded_at_ms=start_ms,
                           duration_ms=duration_ms or DEFAULT_DURATION_MS, tier=tier,
                           has_audio=has_audio, has_video=has_video)
        _private_write(out, sealed)
        raw_path.unlink(missing_ok=True)
        record("sentinel.read", NUXIVA, "sentinel.media.encrypted", {"camera": camera_id, "segment": segment_id},
               sensitivity="household", source="nvr", place=camera_id, at=start_ms / 1000)
        return out

    def header(self, path: Path) -> dict | None:
        with open(path, "rb") as handle:
            prefix = handle.read(8 + nvm2.MAX_HEADER)
        if prefix[:4] != nvm2.MAGIC:
            return None
        header, _, start = self._parse(prefix)
        return {**header, "data_start": start, "file_bytes": path.stat().st_size}

    def _parse(self, prefix: bytes) -> tuple[dict, bytes, int]:
        engine = self._engine()
        if engine is None:
            return nvm2.py_header(prefix)
        text, start = engine.header_v2(prefix)
        return json.loads(text), prefix[8:start], start

    def decrypt_file(self, camera_id: str, segment_path: Path) -> bytes:
        data = segment_path.read_bytes()
        if data[:4] == nvm2.MAGIC:
            engine = self._engine()
            if engine is not None:
                _, plain = engine.open_v2(data)
                plain = bytes(plain)
            else:
                _, plain = nvm2.py_open(self._master_key(), data)
        else:
            plain = legacy.open_v1(self._master_key(), clean_id(camera_id), clean_id(segment_path.stem), data,
                                   day_str(segment_path.stat().st_mtime))
        self._audit_read(camera_id, segment_path.stem)
        return plain

    def read_range(self, camera_id: str, segment_path: Path, start: int, end: int) -> Iterator[bytes]:
        info = self.header(segment_path)
        if info is None:
            data = self.decrypt_file(camera_id, segment_path)
            yield data[start:end + 1]
            return
        if info["camera_id"] != camera_id:
            raise VaultError("nvr.segment.camera_mismatch")
        span = nvm2.chunk_span(info["plain_bytes"], start, end)
        if span is None:
            return
        engine = self._engine()
        master = None if engine is not None else self._master_key()
        self._audit_read(camera_id, segment_path.stem)
        with open(segment_path, "rb") as handle:
            prefix = handle.read(info["data_start"])
            for index in range(span[0], span[1] + 1):
                handle.seek(nvm2.frame_offset(info["data_start"], index))
                frame = handle.read(nvm2.frame_len(info, index))
                plain = bytes(engine.open_chunk_v2(prefix, index, frame)) if engine is not None \
                    else nvm2.py_open_chunk(master, prefix, index, frame)
                base = index * CHUNK_SIZE
                yield plain[max(0, start - base):max(0, end + 1 - base)]

    def stream_chunks(self, camera_id: str, segment_path: Path) -> Iterator[bytes]:
        info = self.header(segment_path)
        if info is None:
            data = self.decrypt_file(camera_id, segment_path)
            for offset in range(0, len(data), CHUNK_SIZE):
                yield data[offset:offset + CHUNK_SIZE]
            return
        yield from self.read_range(camera_id, segment_path, 0, max(0, info["plain_bytes"] - 1))

    def _audit_read(self, camera_id: str, segment_id: str) -> None:
        now = time.monotonic()
        key = (camera_id, segment_id)
        if now - self._audited.get(key, -AUDIT_EVERY) < AUDIT_EVERY:
            return
        if len(self._audited) > 4096:
            self._audited.clear()
        self._audited[key] = now
        record("sentinel.read", NUXIVA, "sentinel.media.playback", {"camera": camera_id, "segment": segment_id},
               sensitivity="sensitive", source="nvr", place=camera_id)

    def is_expired(self, tier: str, recorded_at: int, now: int) -> bool:
        t = tier.lower()
        if t == "pinned":
            return False
        limit = self.event_seconds if "event" in t else self.continuous_seconds
        return (now - recorded_at) > limit

    def delete(self, camera_id: str, segment_id: str) -> bool:
        path = self.path_for(camera_id, segment_id)
        existed = path.exists()
        path.unlink(missing_ok=True)
        return existed

    def list_segments(self, camera_id: str) -> list[dict]:
        cam_dir = self.root / clean_id(camera_id)
        out = []
        for p in sorted(cam_dir.glob("*.nvm")) if cam_dir.exists() else []:
            try:
                st = p.stat()
                out.append({"id": p.stem, "size": st.st_size, "mtime": st.st_mtime})
            except OSError as exc:
                log.debug("NVR: segmento illeggibile %s: %s", p.name, exc)
        return out

    def quota_bytes(self, storage_percent: float = 20.0, storage_max_gb: float = 0.0) -> int:
        self.root.mkdir(parents=True, exist_ok=True)
        total = shutil.disk_usage(self.root).total
        calc = int(total * (max(1.0, min(90.0, float(storage_percent))) / 100.0))
        if storage_max_gb > 0:
            calc = min(calc, int(storage_max_gb * 1024 ** 3))
        return calc

    def storage_stats(self, storage_percent: float = 20.0, storage_max_gb: float = 0.0) -> dict:
        self.root.mkdir(parents=True, exist_ok=True)
        usage = shutil.disk_usage(self.root)
        quota = self.quota_bytes(storage_percent, storage_max_gb)
        files = list(self.root.glob("*/*.nvm"))
        used = sum(f.stat().st_size for f in files if f.exists())
        return {"disk_total_bytes": usage.total, "disk_free_bytes": usage.free, "storage_percent": storage_percent,
                "storage_max_gb": storage_max_gb, "quota_bytes": quota, "vault_used_bytes": used,
                "vault_segments": len(files), "quota_used_percent": round(used / max(1, quota) * 100.0, 1)}


media_vault = MediaVault()
