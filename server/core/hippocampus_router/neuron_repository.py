import logging
import os
import tempfile
from pathlib import Path
from typing import Optional

from server.core.core_platform.errors import CortexFailure, fail
from server.core.core_platform.result import Ok, Result
from server.core.core_platform.zero_trust_crypto import ZeroTrustVault

logger = logging.getLogger("nuxiva.hippocampus.storage")

PURPOSE = "neuron-index"
ASSOCIATED_DATA = b"nuxiva.cortex.neuron-index.v1"
MAX_STORAGE_BYTES = 268_435_456
UNREADABLE_CODES = frozenset({"cortex.crypto.decryption_failed", "cortex.crypto.malformed_ciphertext"})


class EncryptedNeuronRepository:
    def __init__(self, path: Path, vault: ZeroTrustVault) -> None:
        self._path = path
        self._vault = vault

    def _read_bytes(self) -> Result[Optional[bytes], CortexFailure]:
        try:
            if not self._path.is_file():
                return Ok(None)
            if self._path.stat().st_size > MAX_STORAGE_BYTES:
                return fail("hippocampus.storage.corrupted")
            return Ok(self._path.read_bytes())
        except OSError as exc:
            logger.error("Cannot read the neuron memory (%s)", type(exc).__name__)
            return fail("platform.storage.io_failed")

    def load(self) -> Result[Optional[str], CortexFailure]:
        raw = self._read_bytes()
        if not raw.is_ok or raw.value is None:
            return raw
        opened = self._vault.open_bytes(PURPOSE, raw.value, ASSOCIATED_DATA)
        if not opened.is_ok:
            return fail("hippocampus.storage.undecryptable") if opened.error.code in UNREADABLE_CODES else opened
        try:
            return Ok(opened.value.decode("utf-8"))
        except UnicodeDecodeError:
            return fail("hippocampus.storage.corrupted")

    def save(self, snapshot_json: str) -> Result[None, CortexFailure]:
        sealed = self._vault.seal_bytes(PURPOSE, snapshot_json.encode("utf-8"), ASSOCIATED_DATA)
        if not sealed.is_ok:
            return sealed
        temporary: Optional[str] = None
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            descriptor, temporary = tempfile.mkstemp(prefix=".neurons-", suffix=".tmp", dir=self._path.parent)
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(sealed.value)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, self._path)
            temporary = None
            return Ok(None)
        except OSError as exc:
            logger.error("Cannot persist the neuron memory (%s)", type(exc).__name__)
            return fail("platform.storage.io_failed")
        finally:
            if temporary is not None:
                self._discard(temporary)

    @staticmethod
    def _discard(temporary: str) -> None:
        try:
            Path(temporary).unlink(missing_ok=True)
        except OSError as exc:
            logger.error("Cannot remove the temporary neuron memory (%s)", type(exc).__name__)
