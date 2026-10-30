import io
import os
import secrets
from pathlib import Path

import numpy as np
from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

try:
    import nuxiva_native
except ImportError:
    nuxiva_native = None

MAGIC = b"NXBIO1\n"
LEGACY = b"\x93NUMPY"
CONTEXT = b"nuxiva.biometrics.rows.v1"
KEY_LEN = 32
NONCE_LEN = 12
TAG_LEN = 16
MAX_FILE = 16 * 1024 * 1024
MAX_ROWS = 4096
MAX_DIM = 4096
_keys: dict[tuple, bytes] = {}


class SealedRowsError(ValueError):
    pass


def key_path() -> Path:
    explicit = os.environ.get("NUXIVA_BIOMETRIC_KEY")
    if explicit:
        return Path(explicit)
    return Path(os.environ.get("NUXIVA_STATE_ROOT", "/")).resolve() / "etc/nuxiva/biometrics.key"


def native_ready() -> bool:
    return nuxiva_native is not None and hasattr(nuxiva_native, "cortex_seal")


def _write_private(path: Path, data: bytes) -> Path:
    tmp = path.with_name(f".{path.name}.{secrets.token_hex(8)}.tmp")
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "wb") as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())
    return tmp


def _create_master(path: Path) -> None:
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    tmp = _write_private(path, secrets.token_bytes(KEY_LEN))
    try:
        os.link(tmp, path)
    except FileExistsError:
        pass
    finally:
        tmp.unlink(missing_ok=True)


def _master(path: Path) -> tuple[bytes, os.stat_result]:
    if not path.exists():
        _create_master(path)
    info = path.stat()
    if info.st_mode & 0o077:
        path.chmod(0o600)
    master = path.read_bytes()
    if len(master) != KEY_LEN or not any(master):
        raise SealedRowsError("biometrics.key.invalid")
    return master, info


def _derive(master: bytes) -> bytes:
    if native_ready():
        return bytes(nuxiva_native.cortex_derive_key(master, CONTEXT))
    return HKDF(algorithm=hashes.SHA256(), length=KEY_LEN, salt=None, info=CONTEXT).derive(master)


def _key() -> bytes:
    path = key_path()
    master, info = _master(path)
    marker = (str(path), info.st_ino, info.st_mtime_ns)
    key = _keys.get(marker)
    if key is None:
        _keys.clear()
        key = _keys[marker] = _derive(master)
    return key


def _aad(path: Path) -> bytes:
    return b"|".join((CONTEXT, path.parent.name.encode(), path.name.encode()))


def _seal(key: bytes, aad: bytes, data: bytes) -> bytes:
    if native_ready():
        return bytes(nuxiva_native.cortex_seal(key, aad, data))
    nonce = secrets.token_bytes(NONCE_LEN)
    return nonce + AESGCM(key).encrypt(nonce, data, aad)


def _open(key: bytes, aad: bytes, blob: bytes) -> bytes:
    if len(blob) < NONCE_LEN + TAG_LEN:
        raise SealedRowsError("biometrics.rows.malformed")
    try:
        if native_ready():
            return bytes(nuxiva_native.cortex_open(key, aad, blob))
        return AESGCM(key).decrypt(blob[:NONCE_LEN], blob[NONCE_LEN:], aad)
    except (InvalidTag, ValueError) as exc:
        raise SealedRowsError("biometrics.rows.tampered") from exc


def _validate(matrix: np.ndarray) -> np.ndarray:
    if matrix.ndim == 1:
        matrix = matrix[None, :]
    if matrix.ndim != 2 or matrix.dtype.kind != "f":
        raise SealedRowsError("biometrics.rows.shape")
    rows, dim = matrix.shape
    if rows > MAX_ROWS or not 0 < dim <= MAX_DIM or not np.isfinite(matrix).all():
        raise SealedRowsError("biometrics.rows.shape")
    return np.ascontiguousarray(matrix, dtype=np.float32)


def _encode(rows: np.ndarray) -> bytes:
    buffer = io.BytesIO()
    np.save(buffer, _validate(np.asarray(rows)), allow_pickle=False)
    return buffer.getvalue()


def _decode(data: bytes) -> np.ndarray:
    try:
        matrix = np.load(io.BytesIO(data), allow_pickle=False)
    except (ValueError, OSError, EOFError) as exc:
        raise SealedRowsError("biometrics.rows.malformed") from exc
    if not isinstance(matrix, np.ndarray):
        raise SealedRowsError("biometrics.rows.malformed")
    return _validate(matrix)


def is_sealed(path: Path) -> bool:
    with path.open("rb") as handle:
        return handle.read(len(MAGIC)) == MAGIC


def save(path: Path, rows: np.ndarray) -> None:
    blob = MAGIC + _seal(_key(), _aad(path), _encode(rows))
    tmp = _write_private(path, blob)
    try:
        os.replace(tmp, path)
    finally:
        tmp.unlink(missing_ok=True)


def load(path: Path) -> np.ndarray | None:
    if not path.is_file():
        return None
    if path.stat().st_size > MAX_FILE:
        raise SealedRowsError("biometrics.rows.too_large")
    blob = path.read_bytes()
    if blob.startswith(MAGIC):
        return _decode(_open(_key(), _aad(path), blob[len(MAGIC):]))
    if blob.startswith(LEGACY):
        rows = _decode(blob)
        save(path, rows)
        return rows
    raise SealedRowsError("biometrics.rows.format")
