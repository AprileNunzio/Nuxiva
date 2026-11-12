import json
import os
import re
import secrets
import struct
from pathlib import Path

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

MAGIC = b"NXSCRIBE1"
KEY_LEN = 32
NONCE_LEN = 12
NAME = re.compile(r"^[A-Za-z0-9_-]{1,64}__[A-Za-z0-9_-]{1,64}$")
MAX_JOB = 64 * 1024 * 1024
MAX_HEADER = 16 * 1024
MAX_QUEUE = 64


class SpoolError(ValueError):
    pass


def root() -> Path:
    return Path(os.environ.get("NUXIVA_NVR_SCRIBE_DIR", "/var/lib/nuxiva/nvr_scribe"))


def key_path() -> Path:
    explicit = os.environ.get("NUXIVA_NVR_SCRIBE_KEY")
    if explicit:
        return Path(explicit)
    return Path(os.environ.get("NUXIVA_STATE_ROOT", "/")).resolve() / "etc/nuxiva/nvr-scribe.key"


def _private(path: Path, data: bytes) -> None:
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


def master() -> bytes:
    path = key_path()
    if not path.exists():
        path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        tmp = path.with_name(f".{path.name}.{secrets.token_hex(6)}.tmp")
        fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "wb") as handle:
            handle.write(secrets.token_bytes(KEY_LEN))
        try:
            os.link(tmp, path)
        except FileExistsError:
            pass
        finally:
            tmp.unlink(missing_ok=True)
    key = path.read_bytes()
    if len(key) != KEY_LEN or not any(key):
        raise SpoolError("scribe.key.invalid")
    return key


def _key(kind: str) -> bytes:
    return HKDF(algorithm=hashes.SHA256(), length=KEY_LEN, salt=b"nuxiva.nvr.scribe.v1",
                info=kind.encode()).derive(master())


def job_name(camera: str, segment: str) -> str:
    name = f"{camera}__{segment}"
    if not NAME.match(name):
        raise SpoolError("scribe.name.invalid")
    return name


def seal(kind: str, name: str, header: dict, payload: bytes = b"") -> bytes:
    head = json.dumps(header, separators=(",", ":"), ensure_ascii=False).encode()
    if len(head) > MAX_HEADER:
        raise SpoolError("scribe.header.too_large")
    plain = struct.pack(">I", len(head)) + head + payload
    nonce = secrets.token_bytes(NONCE_LEN)
    return MAGIC + nonce + AESGCM(_key(kind)).encrypt(nonce, plain, f"{kind}|{name}".encode())


def open_(kind: str, name: str, blob: bytes) -> tuple[dict, bytes]:
    if not blob.startswith(MAGIC) or len(blob) > MAX_JOB + 1024:
        raise SpoolError("scribe.blob.invalid")
    nonce = blob[len(MAGIC):len(MAGIC) + NONCE_LEN]
    plain = AESGCM(_key(kind)).decrypt(nonce, blob[len(MAGIC) + NONCE_LEN:], f"{kind}|{name}".encode())
    size = struct.unpack(">I", plain[:4])[0]
    if size > MAX_HEADER:
        raise SpoolError("scribe.header.too_large")
    return json.loads(plain[4:4 + size].decode()), plain[4 + size:]


def folder(kind: str) -> Path:
    if kind not in ("jobs", "done"):
        raise SpoolError("scribe.kind.invalid")
    return root() / kind


def put(kind: str, name: str, header: dict, payload: bytes = b"") -> Path:
    if len(payload) > MAX_JOB:
        raise SpoolError("scribe.job.too_large")
    path = folder(kind) / f"{job_name(*name.split('__', 1))}.nxs"
    _private(path, seal(kind, name, header, payload))
    return path


def take(kind: str, name: str) -> tuple[dict, bytes]:
    path = folder(kind) / f"{job_name(*name.split('__', 1))}.nxs"
    try:
        return open_(kind, name, path.read_bytes())
    finally:
        path.unlink(missing_ok=True)


def names(kind: str) -> list[str]:
    base = folder(kind)
    if not base.exists():
        return []
    rows = sorted(base.glob("*.nxs"), key=lambda p: p.stat().st_mtime)
    return [p.stem for p in rows if NAME.match(p.stem)]


def pending(kind: str) -> int:
    return len(names(kind))
