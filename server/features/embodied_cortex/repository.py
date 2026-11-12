import logging
import os
import tempfile
from pathlib import Path
from typing import Optional

from server.core.core_platform.errors import CortexFailure, fail
from server.core.core_platform.result import Ok, Result
from server.core.core_platform.zero_trust_crypto import ZeroTrustVault

logger = logging.getLogger("nuxiva.embodied_cortex.storage")

MAX_STORAGE_BYTES = 16_777_216
UNREADABLE_CODES = frozenset(
    {"cortex.crypto.decryption_failed", "cortex.crypto.malformed_ciphertext"}
)


class EncryptedCortexRepository:
    def __init__(self, path: Path, vault: ZeroTrustVault, purpose: str, associated: bytes) -> None:
        self._path = path
        self._vault = vault
        self._purpose = purpose
        self._associated = associated

    def _read_bytes(self) -> Result[Optional[bytes], CortexFailure]:
        try:
            if not self._path.is_file():
                return Ok(None)
            if self._path.stat().st_size > MAX_STORAGE_BYTES:
                return fail("hippocampus.storage.corrupted")
            return Ok(self._path.read_bytes())
        except OSError as exc:
            logger.error("Cannot read sealed cortex state (%s)", type(exc).__name__)
            return fail("platform.storage.io_failed")

    def load(self) -> Result[Optional[str], CortexFailure]:
        raw = self._read_bytes()
        if not raw.is_ok or raw.value is None:
            return raw
        opened = self._vault.open_bytes(self._purpose, raw.value, self._associated)
        if not opened.is_ok:
            if opened.error.code in UNREADABLE_CODES:
                return fail("hippocampus.storage.undecryptable")
            return opened
        try:
            return Ok(opened.value.decode("utf-8"))
        except UnicodeDecodeError:
            return fail("hippocampus.storage.corrupted")

    def save(self, snapshot_json: str) -> Result[None, CortexFailure]:
        sealed = self._vault.seal_bytes(
            self._purpose,
            snapshot_json.encode("utf-8"),
            self._associated,
        )
        if not sealed.is_ok:
            return sealed
        temporary: Optional[str] = None
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            descriptor, temporary = tempfile.mkstemp(
                prefix=".embodied-",
                suffix=".tmp",
                dir=self._path.parent,
            )
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(sealed.value)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, self._path)
            temporary = None
            return Ok(None)
        except OSError as exc:
            logger.error("Cannot persist sealed cortex state (%s)", type(exc).__name__)
            return fail("platform.storage.io_failed")
        finally:
            if temporary is not None:
                self._discard(temporary)

    @staticmethod
    def _discard(temporary: str) -> None:
        try:
            Path(temporary).unlink(missing_ok=True)
        except OSError as exc:
            logger.error("Cannot remove temporary cortex state (%s)", type(exc).__name__)
