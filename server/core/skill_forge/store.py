import base64
import json
import logging
import os
import tempfile
import threading
import time
from pathlib import Path
from typing import Any, Optional

from server.core.core_platform.errors import CortexFailure, fail
from server.core.core_platform.result import Ok, Result
from server.core.core_platform.zero_trust_crypto import SignedBlob, ZeroTrustVault

logger = logging.getLogger("nuxiva.skill_forge.store")

SEAL_PURPOSE = "skill-registry"
SIGN_PURPOSE = "skill-code"
ASSOCIATED = b"nuxiva.cortex.skills.v1"
MAX_STORAGE_BYTES = 67_108_864


def _b64(raw: bytes) -> str:
    return base64.b64encode(raw).decode("ascii")


class SkillStore:
    def __init__(self, path: Path, vault: ZeroTrustVault) -> None:
        self._path = path
        self._vault = vault
        self._records: Optional[dict[str, dict[str, Any]]] = None
        self._lock = threading.RLock()

    def _load(self) -> Result[dict[str, dict[str, Any]], CortexFailure]:
        try:
            if not self._path.is_file():
                return Ok({})
            if self._path.stat().st_size > MAX_STORAGE_BYTES:
                return fail("hippocampus.storage.corrupted")
            raw = self._path.read_bytes()
        except OSError as exc:
            logger.error("Cannot read the skill registry (%s)", type(exc).__name__)
            return fail("platform.storage.io_failed")
        opened = self._vault.open_json(SEAL_PURPOSE, raw, ASSOCIATED)
        if not opened.is_ok:
            return fail("hippocampus.storage.undecryptable")
        return Ok(opened.value) if isinstance(opened.value, dict) else fail("hippocampus.storage.corrupted")

    def _records_or_fail(self) -> Result[dict[str, dict[str, Any]], CortexFailure]:
        if self._records is None:
            loaded = self._load()
            if not loaded.is_ok:
                return loaded
            self._records = loaded.value
        return Ok(self._records)

    def _flush(self, records: dict[str, dict[str, Any]]) -> Result[None, CortexFailure]:
        sealed = self._vault.seal_json(SEAL_PURPOSE, records, ASSOCIATED)
        if not sealed.is_ok:
            return sealed
        temporary: Optional[str] = None
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            descriptor, temporary = tempfile.mkstemp(prefix=".skills-", suffix=".tmp", dir=self._path.parent)
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(sealed.value)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, self._path)
            temporary = None
            return Ok(None)
        except OSError as exc:
            logger.error("Cannot persist the skill registry (%s)", type(exc).__name__)
            return fail("platform.storage.io_failed")
        finally:
            if temporary is not None:
                self._discard(temporary)

    @staticmethod
    def _discard(temporary: str) -> None:
        try:
            Path(temporary).unlink(missing_ok=True)
        except OSError as exc:
            logger.error("Cannot remove a temporary skill file (%s)", type(exc).__name__)

    def put(self, neuron_id: str, title: str, payload: dict[str, Any], origin: str, synthetic: int) -> Result[None, CortexFailure]:
        body = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        signed = self._vault.sign(SIGN_PURPOSE, body)
        if not signed.is_ok:
            return signed
        with self._lock:
            current = self._records_or_fail()
            if not current.is_ok:
                return current
            updated = dict(current.value)
            updated[neuron_id] = {
                "title": title, "origin": origin, "synthetic_utterances": synthetic, "created_at": time.time(),
                "payload": _b64(body), "signature": _b64(signed.value.signature), "public_key": _b64(signed.value.public_key),
            }
            flushed = self._flush(updated)
            if flushed.is_ok:
                self._records = updated
            return flushed

    def remove(self, neuron_id: str) -> Result[bool, CortexFailure]:
        with self._lock:
            current = self._records_or_fail()
            if not current.is_ok:
                return current
            if neuron_id not in current.value:
                return Ok(False)
            updated = {key: value for key, value in current.value.items() if key != neuron_id}
            flushed = self._flush(updated)
            if not flushed.is_ok:
                return flushed
            self._records = updated
            return Ok(True)

    def trusted_payload(self, neuron_id: str) -> Result[dict[str, Any], CortexFailure]:
        with self._lock:
            current = self._records_or_fail()
            if not current.is_ok:
                return current
            record = current.value.get(neuron_id)
        if record is None:
            return fail("cortex.forge.unknown_skill")
        try:
            blob = SignedBlob(base64.b64decode(record["payload"]), base64.b64decode(record["signature"]),
                              base64.b64decode(record["public_key"]))
            payload = json.loads(blob.payload)
        except (KeyError, ValueError, TypeError):
            return fail("cortex.forge.untrusted")
        verified = self._vault.verify(SIGN_PURPOSE, blob)
        if not verified.is_ok:
            return verified
        return Ok(payload) if verified.value and isinstance(payload, dict) else fail("cortex.forge.untrusted")

    def listing(self) -> Result[list[dict[str, Any]], CortexFailure]:
        with self._lock:
            current = self._records_or_fail()
            if not current.is_ok:
                return current
            return Ok([{"neuron_id": key, "title": value["title"], "origin": value["origin"],
                        "synthetic_utterances": value["synthetic_utterances"], "created_at": value["created_at"]}
                       for key, value in sorted(current.value.items())])
