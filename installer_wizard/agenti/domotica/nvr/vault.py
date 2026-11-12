import hashlib
import hmac
import json
import logging
import os
import secrets
import struct
import time
from datetime import datetime
from pathlib import Path
from typing import Generator

from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305

from config import STATE_DIR
from agenti.sentinel import vault as sentinel_vault
from agenti.sentinel.record import NUXIVA, record
import native_module

log = logging.getLogger("nuxiva.nvr.vault")
CHUNK_SIZE = 65536
VAULT_DIR = STATE_DIR / "cameras" / "vault"


def _rust_vault_class():
    return native_module.feature("RustMediaVault")


def day_str(ts: float | None = None) -> str:
    return datetime.fromtimestamp(ts or time.time()).strftime("%Y-%m-%d")


def derive_day_key(master_key: bytes, camera_id: str, day: str) -> bytes:
    prk = hmac.new(b"nuxiva.vault_media.salt.v1", master_key, hashlib.sha256).digest()
    info = f"camera:{camera_id}|day:{day}".encode("utf-8")
    return hmac.new(prk, info + b"\x01", hashlib.sha256).digest()[:32]


def derive_seg_key(day_key: bytes, segment_id: str) -> bytes:
    prk = hmac.new(b"nuxiva.vault_media.segment.salt", day_key, hashlib.sha256).digest()
    return hmac.new(prk, segment_id.encode("utf-8") + b"\x01", hashlib.sha256).digest()[:32]


class MediaVault:
    def __init__(self, continuous_seconds: int = 7200, event_seconds: int = 604800) -> None:
        self.continuous_seconds = continuous_seconds
        self.event_seconds = event_seconds
        self.root = VAULT_DIR
        self.root.mkdir(parents=True, exist_ok=True)

    def _master_key(self) -> bytes:
        try:
            return sentinel_vault.secret("media")
        except Exception:
            path = self.root / ".master.key"
            if not path.exists():
                path.write_bytes(secrets.token_bytes(32))
                os.chmod(path, 0o600)
            return path.read_bytes()

    def _engine(self):
        cls = _rust_vault_class()
        if cls:
            try:
                return cls(self._master_key(), self.continuous_seconds, self.event_seconds)
            except Exception as exc:
                log.debug("RustMediaVault initialization fallback: %s", exc)
        return None

    def encrypt_file(self, camera_id: str, raw_path: Path, tier: str = "continuous",
                     has_audio: bool = True, has_video: bool = True) -> Path:
        raw_bytes = raw_path.read_bytes()
        segment_id = raw_path.stem
        now = time.time()
        day = day_str(now)
        recorded_at = int(now)
        duration_ms = 60000

        cam_dir = self.root / camera_id
        cam_dir.mkdir(parents=True, exist_ok=True)
        out_path = cam_dir / f"{segment_id}.nvm"

        engine = self._engine()
        if engine:
            nonce_bytes = secrets.token_bytes(24)
            enc_data = engine.encrypt_segment(
                camera_id, day, segment_id, recorded_at, duration_ms,
                has_audio, has_video, tier, nonce_bytes, raw_bytes
            )
        else:
            enc_data = self._py_encrypt(
                camera_id, day, segment_id, recorded_at, duration_ms,
                has_audio, has_video, tier, raw_bytes
            )

        out_path.write_bytes(bytes(enc_data))
        os.chmod(out_path, 0o600)

        try:
            raw_path.unlink(missing_ok=True)
        except OSError:
            pass

        record(
            "sentinel.read", NUXIVA, "sentinel.media.encrypted",
            {"camera": camera_id, "segment": segment_id},
            sensitivity="household", source="nvr", place=camera_id, at=now
        )
        return out_path

    def _py_encrypt(self, camera_id: str, day: str, segment_id: str,
                    recorded_at: int, duration_ms: int, has_audio: bool,
                    has_video: bool, tier: str, raw_media: bytes) -> bytes:
        day_key = derive_day_key(self._master_key(), camera_id, day)
        seg_key = derive_seg_key(day_key, segment_id)
        nonce_base = secrets.token_bytes(12)
        cipher = ChaCha20Poly1305(seg_key)

        chunks = []
        for idx, offset in enumerate(range(0, len(raw_media), CHUNK_SIZE)):
            chunk = raw_media[offset:offset + CHUNK_SIZE]
            idx_bytes = struct.pack(">Q", idx)
            chunk_nonce = nonce_base[:4] + idx_bytes
            ct = cipher.encrypt(chunk_nonce, chunk, None)
            chunks.append(chunk_nonce + ct)

        meta = {
            "segment_id": segment_id,
            "camera_id": camera_id,
            "day": day,
            "recorded_at": recorded_at,
            "duration_ms": duration_ms,
            "has_audio": has_audio,
            "has_video": has_video,
            "tier": tier.capitalize(),
            "total_plaintext_bytes": len(raw_media),
            "chunk_count": len(chunks),
        }
        meta_json = json.dumps(meta).encode("utf-8")
        out = bytearray(b"NVM1")
        out.extend(struct.pack(">I", len(meta_json)))
        out.extend(meta_json)
        for c in chunks:
            out.extend(struct.pack(">I", len(c)))
            out.extend(c)
        return bytes(out)

    def decrypt_file(self, camera_id: str, segment_path: Path) -> bytes:
        data = segment_path.read_bytes()
        segment_id = segment_path.stem
        day = day_str(segment_path.stat().st_mtime)

        engine = self._engine()
        if engine:
            try:
                dec = engine.decrypt_segment(camera_id, day, segment_id, data)
                self._audit_read(camera_id, segment_id)
                return bytes(dec)
            except Exception as exc:
                log.debug("RustMediaVault decrypt fallback: %s", exc)

        dec = self._py_decrypt(camera_id, day, segment_id, data)
        self._audit_read(camera_id, segment_id)
        return dec

    def _py_decrypt(self, camera_id: str, day: str, segment_id: str, data: bytes) -> bytes:
        if len(data) < 8 or data[:4] != b"NVM1":
            raise ValueError("Invalid media segment format")
        meta_len = struct.unpack(">I", data[4:8])[0]
        meta = json.loads(data[8:8 + meta_len].decode("utf-8"))

        day_key = derive_day_key(self._master_key(), camera_id, meta.get("day", day))
        seg_key = derive_seg_key(day_key, segment_id)
        cipher = ChaCha20Poly1305(seg_key)

        offset = 8 + meta_len
        out = bytearray()
        while offset < len(data):
            clen = struct.unpack(">I", data[offset:offset + 4])[0]
            offset += 4
            chunk_blob = data[offset:offset + clen]
            offset += clen
            chunk_nonce = chunk_blob[:12]
            ct = chunk_blob[12:]
            out.extend(cipher.decrypt(chunk_nonce, ct, None))
        return bytes(out)

    def stream_chunks(self, camera_id: str, segment_path: Path) -> Generator[bytes, None, None]:
        decrypted = self.decrypt_file(camera_id, segment_path)
        for offset in range(0, len(decrypted), CHUNK_SIZE):
            yield decrypted[offset:offset + CHUNK_SIZE]

    def _audit_read(self, camera_id: str, segment_id: str) -> None:
        record(
            "sentinel.read", NUXIVA, "sentinel.media.playback",
            {"camera": camera_id, "segment": segment_id},
            sensitivity="sensitive", source="nvr", place=camera_id
        )

    def is_expired(self, tier: str, recorded_at: int, now: int) -> bool:
        t = tier.lower()
        if t == "pinned":
            return False
        engine = self._engine()
        if engine:
            return engine.is_expired(t, recorded_at, now)
        limit = self.event_seconds if "event" in t else self.continuous_seconds
        return (now - recorded_at) > limit

    def prune(self, camera_id: str, now: float | None = None) -> int:
        cam_dir = self.root / camera_id
        if not cam_dir.exists():
            return 0
        current = int(now or time.time())
        removed = 0
        for p in cam_dir.glob("*.nvm"):
            try:
                mtime = int(p.stat().st_mtime)
                if self.is_expired("continuous", mtime, current):
                    p.unlink(missing_ok=True)
                    removed += 1
            except OSError:
                pass
        return removed

    def list_segments(self, camera_id: str) -> list[dict]:
        cam_dir = self.root / camera_id
        if not cam_dir.exists():
            return []
        out = []
        for p in sorted(cam_dir.glob("*.nvm")):
            try:
                st = p.stat()
                out.append({
                    "id": p.stem,
                    "size": st.st_size,
                    "mtime": st.st_mtime,
                    "path": str(p),
                })
            except OSError:
                pass
    def quota_bytes(self, storage_percent: float = 20.0, storage_max_gb: float = 0.0) -> int:
        import shutil
        try:
            usage = shutil.disk_usage(self.root)
            total = usage.total
        except OSError:
            total = 100 * 1024 * 1024 * 1024
        calc = int(total * (max(1.0, min(90.0, float(storage_percent))) / 100.0))
        if storage_max_gb > 0:
            calc = min(calc, int(storage_max_gb * 1024 * 1024 * 1024))
        return calc

    def storage_stats(self, storage_percent: float = 20.0, storage_max_gb: float = 0.0) -> dict:
        import shutil
        try:
            usage = shutil.disk_usage(self.root)
            disk_total = usage.total
            disk_free = usage.free
        except OSError:
            disk_total = 100 * 1024 * 1024 * 1024
            disk_free = 50 * 1024 * 1024 * 1024
        quota = self.quota_bytes(storage_percent, storage_max_gb)
        files = list(self.root.glob("*/*.nvm"))
        used_bytes = sum(f.stat().st_size for f in files if f.exists())
        return {
            "disk_total_bytes": disk_total,
            "disk_free_bytes": disk_free,
            "storage_percent": storage_percent,
            "storage_max_gb": storage_max_gb,
            "quota_bytes": quota,
            "vault_used_bytes": used_bytes,
            "vault_segments": len(files),
            "quota_used_percent": round((used_bytes / max(1, quota)) * 100.0, 1),
        }

    def prune_quota(self, storage_percent: float = 20.0, storage_max_gb: float = 0.0) -> int:
        quota = self.quota_bytes(storage_percent, storage_max_gb)
        files = []
        for p in self.root.glob("*/*.nvm"):
            try:
                st = p.stat()
                files.append((st.st_mtime, st.st_size, p))
            except OSError:
                pass
        total = sum(s for _, s, _ in files)
        if total <= quota:
            return 0
        files.sort(key=lambda x: x[0])
        removed = 0
        for _, size, path in files:
            if total <= quota:
                break
            try:
                path.unlink(missing_ok=True)
                total -= size
                removed += 1
            except OSError:
                pass
        return removed


media_vault = MediaVault()
