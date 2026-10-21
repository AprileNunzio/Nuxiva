import os
import json
import base64
import time
from typing import Dict, Any, Optional
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from server.features.chess_grandmaster_agent.contracts import SessionVaultPayload

class ChessSessionVault:
    def __init__(self, master_secret: Optional[str] = None) -> None:
        raw_secret = master_secret or os.environ.get("NUXIVA_VAULT_KEY", "nuxiva-chess-zero-trust-default-salt-98124")
        self._salt = b"nuxiva_chess_salt_v1"
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=self._salt,
            iterations=100000,
        )
        self._key = kdf.derive(raw_secret.encode())
        self._aesgcm = AESGCM(self._key)
        self._in_memory_store: Dict[str, SessionVaultPayload] = {}

    def encrypt_session(self, session_id: str, user_id: str, state_data: Dict[str, Any]) -> SessionVaultPayload:
        serialized = json.dumps(state_data).encode("utf-8")
        nonce = os.urandom(12)
        ciphertext = self._aesgcm.encrypt(nonce, serialized, None)
        encrypted_data = ciphertext[:-16]
        auth_tag = ciphertext[-16:]

        payload = SessionVaultPayload(
            session_id=session_id,
            user_id=user_id,
            encrypted_state=base64.b64encode(encrypted_data).decode("utf-8"),
            nonce=base64.b64encode(nonce).decode("utf-8"),
            tag=base64.b64encode(auth_tag).decode("utf-8"),
            timestamp=time.time(),
        )
        self._in_memory_store[session_id] = payload
        return payload

    def decrypt_session(self, session_id: str) -> Dict[str, Any]:
        payload = self._in_memory_store.get(session_id)
        if not payload:
            raise KeyError(f"Session '{session_id}' not found in vault")

        nonce = base64.b64decode(payload.nonce)
        encrypted_data = base64.b64decode(payload.encrypted_state)
        tag = base64.b64decode(payload.tag)
        full_ciphertext = encrypted_data + tag

        decrypted_bytes = self._aesgcm.decrypt(nonce, full_ciphertext, None)
        return json.loads(decrypted_bytes.decode("utf-8"))

    def get_session_metadata(self, session_id: str) -> Optional[Dict[str, Any]]:
        payload = self._in_memory_store.get(session_id)
        if not payload:
            return None
        return {
            "session_id": payload.session_id,
            "user_id": payload.user_id,
            "timestamp": payload.timestamp,
        }
