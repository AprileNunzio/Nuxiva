import asyncio
import hashlib
import logging
import os
import re
import tempfile
from pathlib import Path

import httpx

log = logging.getLogger("nuxiva.rpa")
MAGIC = b"NXENROL1"
LENGTH_SIZE = 4
PAYLOAD_LIMIT = 4096
SIZE_LIMIT = 300 * 1024 * 1024
CHUNK = 1024 * 1024
CACHE_DIR = Path(os.environ.get("NUXIVA_INSTALLER_CACHE", "/var/lib/nuxiva/installer-cache"))
OFFICIAL_PREFIX = "https://github.com/AprileNunzio/Nuxiva/releases/download/"
SAFE_VERSION = re.compile(r"\d+(?:\.\d+){1,3}")
_lock = asyncio.Lock()


class InstallerUnavailable(Exception):
    pass


def trailer(payload: bytes) -> bytes:
    if not 0 < len(payload) <= PAYLOAD_LIMIT:
        raise ValueError("enrollment_payload_size")
    return payload + len(payload).to_bytes(LENGTH_SIZE, "big") + MAGIC


def _cache_path(info: dict) -> Path:
    version, digest = str(info.get("version", "")), str(info.get("sha256", ""))
    if not SAFE_VERSION.fullmatch(version) or not re.fullmatch(r"[0-9a-f]{64}", digest):
        raise InstallerUnavailable("installer_digest_missing")
    if not str(info.get("url", "")).startswith(OFFICIAL_PREFIX):
        raise InstallerUnavailable("installer_url_untrusted")
    return CACHE_DIR / f"Nuxiva_Setup-{version}-{digest[:16]}.exe"


def _verified(path: Path, digest: str) -> bool:
    try:
        if not path.is_file() or path.stat().st_size > SIZE_LIMIT:
            return False
        hasher = hashlib.sha256()
        with path.open("rb") as handle:
            for block in iter(lambda: handle.read(CHUNK), b""):
                hasher.update(block)
        return hasher.hexdigest() == digest
    except OSError:
        return False


async def _download(info: dict, target: Path) -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True, mode=0o700)
    handle, temp_name = tempfile.mkstemp(dir=CACHE_DIR, suffix=".part")
    temp = Path(temp_name)
    hasher = hashlib.sha256()
    size = 0
    try:
        with os.fdopen(handle, "wb") as out:
            async with httpx.AsyncClient(timeout=httpx.Timeout(60, connect=10), follow_redirects=True) as client:
                async with client.stream("GET", info["url"]) as response:
                    response.raise_for_status()
                    if not str(response.url).startswith(("https://github.com/", "https://objects.githubusercontent.com/", "https://release-assets.githubusercontent.com/")):
                        raise InstallerUnavailable("installer_redirect_untrusted")
                    async for block in response.aiter_bytes(CHUNK):
                        size += len(block)
                        if size > SIZE_LIMIT:
                            raise InstallerUnavailable("installer_too_large")
                        hasher.update(block)
                        out.write(block)
            out.flush()
            os.fsync(out.fileno())
        if hasher.hexdigest() != info["sha256"]:
            raise InstallerUnavailable("installer_digest_mismatch")
        os.replace(temp, target)
    finally:
        temp.unlink(missing_ok=True)


def _purge(keep: Path) -> None:
    for old in CACHE_DIR.glob("Nuxiva_Setup-*.exe"):
        if old != keep:
            old.unlink(missing_ok=True)


async def base_installer(info: dict) -> Path:
    target = _cache_path(info)
    async with _lock:
        if _verified(target, info["sha256"]):
            return target
        try:
            await _download(info, target)
        except (httpx.HTTPError, OSError) as exc:
            log.warning("Installer Windows non scaricabile da GitHub: %s", exc)
            raise InstallerUnavailable("installer_download_failed") from exc
        _purge(target)
    return target


def stream(path: Path, extra: bytes):
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(CHUNK), b""):
            yield block
    yield extra
