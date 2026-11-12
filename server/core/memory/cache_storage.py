import base64
import hashlib
import hmac
import json
import logging
import os
import tempfile
from pathlib import Path
from typing import Callable

from cryptography.fernet import Fernet, InvalidToken

from server.core.memory.cache_policy import canonical

logger = logging.getLogger("nuxiva.semantic_cache")


class EncryptedCacheStorage:
    def __init__(self, path: str, key_provider: Callable[[], str], max_bytes: int):
        self.path = Path(path)
        self.key_provider = key_provider
        self.max_bytes = max_bytes

    def cipher(self) -> Fernet:
        material = hmac.new(self.key_provider().encode("utf-8"), b"nuxiva.semantic-cache.encryption.v2", hashlib.sha256).digest()
        return Fernet(base64.urlsafe_b64encode(material))

    def load(self) -> list:
        try:
            with self.path.open("rb") as stream:
                encrypted = stream.read(self.max_bytes + 1)
            if len(encrypted) > self.max_bytes:
                logger.warning("Ignoring cache storage larger than configured limit")
                return []
            data = json.loads(self.cipher().decrypt(encrypted))
            if not isinstance(data, dict) or data.get("version") != 2 or not isinstance(data.get("entries"), list):
                logger.warning("Ignoring cache storage with an unsupported schema")
                return []
            return data["entries"]
        except FileNotFoundError:
            return []
        except (OSError, ValueError, InvalidToken) as exc:
            logger.warning("Cannot load encrypted cache; legacy or invalid records ignored (%s)", type(exc).__name__)
            return []

    def save(self, entries: list) -> bool:
        temporary = None
        try:
            encrypted = self.cipher().encrypt(canonical({"version": 2, "entries": entries}))
            if len(encrypted) > self.max_bytes:
                raise ValueError("Cache storage exceeds configured limit")
            self.path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            fd, temporary = tempfile.mkstemp(prefix=".semantic-cache-", suffix=".tmp", dir=self.path.parent)
            with os.fdopen(fd, "wb") as stream:
                stream.write(encrypted)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, self.path)
            return True
        except (OSError, ValueError, TypeError) as exc:
            logger.error("Cannot atomically persist encrypted cache (%s)", type(exc).__name__)
            return False
        finally:
            if temporary is not None:
                try:
                    Path(temporary).unlink(missing_ok=True)
                except OSError as exc:
                    logger.error("Cannot remove temporary cache storage (%s)", type(exc).__name__)

    def clear(self) -> bool:
        try:
            self.path.unlink(missing_ok=True)
            return True
        except OSError as exc:
            logger.error("Cannot remove cache storage (%s)", type(exc).__name__)
            return False
