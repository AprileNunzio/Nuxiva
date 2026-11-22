import base64
import hashlib
import hmac
import json
import os
import re
import secrets
import string
import time
import uuid
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from cryptography.fernet import Fernet, InvalidToken

from server.features.password_vault.models import (
    SecretCategory,
    VaultEntryCreate,
    VaultEntryMetadata,
    VaultEntryRevealed,
    VaultStatusResponse,
)

PBKDF2_ITERATIONS = 240_000
DEFAULT_VAULTS_DIR = Path(__file__).resolve().parents[3] / "data" / "vaults"


def _safe_user_slug(user_id: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9_\-]", "_", user_id.strip())
    if not cleaned:
        raise ValueError("user_id non valido")
    return cleaned[:64]


def _derive_keys(master_password: str, salt: bytes) -> Tuple[bytes, bytes]:
    raw = hashlib.pbkdf2_hmac(
        "sha256",
        master_password.encode("utf-8"),
        salt,
        PBKDF2_ITERATIONS,
        dklen=64,
    )
    fernet_key = base64.urlsafe_b64encode(raw[:32])
    verifier = raw[32:]
    return fernet_key, verifier


def _mask_secret(secret: str) -> str:
    if not secret:
        return ""
    if len(secret) <= 4:
        return "••••"
    return f"{secret[:2]}{'•' * min(10, len(secret) - 4)}{secret[-2:]}"


class UserPasswordVaultService:
    """
    Gestore password cifrato Zero-Trust per utente collegato.
    - Ogni utente ha il proprio archivio cifrato AES-128-CBC + HMAC-SHA256 (Fernet)
      con chiave derivata via PBKDF2-HMAC-SHA256 (240.000 iterazioni).
    - La master password non viene mai salvata su disco.
    - Le liste restituiscono solo metadati mascherati; la decifratura avviene
      esclusivamente a vault sbloccato (in memoria con TTL).
    """

    def __init__(self, storage_dir: Optional[Path] = None) -> None:
        self._storage_dir = Path(storage_dir) if storage_dir else DEFAULT_VAULTS_DIR
        self._storage_dir.mkdir(parents=True, exist_ok=True)
        # user_id -> (Fernet instance, expires_at_ts)
        self._unlocked_sessions: Dict[str, Tuple[Fernet, float]] = {}

    def _vault_path(self, user_id: str) -> Path:
        return self._storage_dir / f"{_safe_user_slug(user_id)}.vault.json"

    def _load_raw(self, user_id: str) -> Optional[dict]:
        path = self._vault_path(user_id)
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def _save_raw(self, user_id: str, data: dict) -> None:
        path = self._vault_path(user_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        try:
            os.chmod(path, 0o600)
        except OSError:
            pass

    def _get_fernet(self, user_id: str) -> Fernet:
        session = self._unlocked_sessions.get(user_id)
        if not session:
            raise PermissionError("Vault bloccato: sblocca prima il gestore password con la master password.")
        fernet, expires_at = session
        if time.time() >= expires_at:
            self._unlocked_sessions.pop(user_id, None)
            raise PermissionError("Sessione vault scaduta: reinserisci la master password.")
        return fernet

    def get_status(self, user_id: str) -> VaultStatusResponse:
        raw = self._load_raw(user_id)
        session = self._unlocked_sessions.get(user_id)
        unlocked = False
        expires_at = None
        if session:
            if time.time() < session[1]:
                unlocked = True
                expires_at = session[1]
            else:
                self._unlocked_sessions.pop(user_id, None)
        return VaultStatusResponse(
            user_id=user_id,
            initialized=raw is not None,
            unlocked=unlocked,
            entry_count=len(raw.get("entries", [])) if raw else 0,
            expires_at=expires_at,
        )

    def unlock_or_initialize(self, user_id: str, master_password: str, ttl_seconds: int = 900) -> VaultStatusResponse:
        raw = self._load_raw(user_id)
        if raw is None:
            salt = os.urandom(16)
            fernet_key, verifier = _derive_keys(master_password, salt)
            raw = {
                "version": 1,
                "user_id": user_id,
                "salt_b64": base64.b64encode(salt).decode("ascii"),
                "verifier_b64": base64.b64encode(verifier).decode("ascii"),
                "created_at": time.time(),
                "entries": [],
            }
            self._save_raw(user_id, raw)
        else:
            salt = base64.b64decode(raw["salt_b64"])
            expected_verifier = base64.b64decode(raw["verifier_b64"])
            fernet_key, actual_verifier = _derive_keys(master_password, salt)
            if not hmac.compare_digest(expected_verifier, actual_verifier):
                raise PermissionError("Master password non valida.")

        self._unlocked_sessions[user_id] = (Fernet(fernet_key), time.time() + ttl_seconds)
        return self.get_status(user_id)

    def lock(self, user_id: str) -> VaultStatusResponse:
        self._unlocked_sessions.pop(user_id, None)
        return self.get_status(user_id)

    def add_entry(self, user_id: str, payload: VaultEntryCreate) -> VaultEntryMetadata:
        fernet = self._get_fernet(user_id)
        raw = self._load_raw(user_id)
        if raw is None:
            raise PermissionError("Vault non inizializzato.")

        now = time.time()
        entry_id = f"sec_{uuid.uuid4().hex[:12]}"
        secret_blob = json.dumps(
            {
                "secret": payload.secret,
                "extra_secret": payload.extra_secret,
                "notes": payload.notes,
            },
            ensure_ascii=False,
        ).encode("utf-8")
        ciphertext = fernet.encrypt(secret_blob).decode("ascii")

        record = {
            "entry_id": entry_id,
            "label": payload.label.strip(),
            "category": payload.category.value,
            "host_or_url": payload.host_or_url.strip(),
            "port": payload.port,
            "username": payload.username.strip(),
            "has_secret": bool(payload.secret),
            "has_extra_secret": bool(payload.extra_secret),
            "masked_preview": _mask_secret(payload.secret),
            "tags": [t.strip() for t in payload.tags if t.strip()],
            "ciphertext": ciphertext,
            "created_at": now,
            "updated_at": now,
        }
        raw.setdefault("entries", []).append(record)
        self._save_raw(user_id, raw)
        return self._to_metadata(record)

    def list_entries(
        self,
        user_id: str,
        category: Optional[SecretCategory] = None,
        query: Optional[str] = None,
    ) -> List[VaultEntryMetadata]:
        raw = self._load_raw(user_id)
        if raw is None:
            return []
        q = (query or "").strip().lower()
        results: List[VaultEntryMetadata] = []
        for rec in raw.get("entries", []):
            if category is not None and rec.get("category") != category.value:
                continue
            if q:
                haystack = " ".join([
                    rec.get("label", ""),
                    rec.get("host_or_url", ""),
                    rec.get("username", ""),
                    " ".join(rec.get("tags", [])),
                ]).lower()
                if q not in haystack:
                    continue
            results.append(self._to_metadata(rec))
        return results

    def reveal_entry(self, user_id: str, entry_id: str) -> VaultEntryRevealed:
        fernet = self._get_fernet(user_id)
        raw = self._load_raw(user_id)
        if raw is None:
            raise KeyError("Vault non trovato.")

        for rec in raw.get("entries", []):
            if rec.get("entry_id") == entry_id:
                try:
                    decrypted = json.loads(fernet.decrypt(rec["ciphertext"].encode("ascii")).decode("utf-8"))
                except InvalidToken as exc:
                    raise PermissionError("Impossibile decifrare la voce del vault.") from exc
                meta = self._to_metadata(rec)
                return VaultEntryRevealed(
                    **meta.model_dump(exclude={"notes"}),
                    notes=decrypted.get("notes", ""),
                    secret=decrypted.get("secret", ""),
                    extra_secret=decrypted.get("extra_secret", ""),
                )
        raise KeyError(f"Voce '{entry_id}' non trovata nel vault.")

    def delete_entry(self, user_id: str, entry_id: str) -> bool:
        self._get_fernet(user_id)
        raw = self._load_raw(user_id)
        if raw is None:
            return False
        entries = raw.get("entries", [])
        new_entries = [e for e in entries if e.get("entry_id") != entry_id]
        if len(new_entries) == len(entries):
            return False
        raw["entries"] = new_entries
        self._save_raw(user_id, raw)
        return True

    def generate_strong_password(self, length: int = 20, include_symbols: bool = True) -> str:
        length = max(12, min(64, int(length)))
        alphabet = string.ascii_letters + string.digits
        if include_symbols:
            alphabet += "!@#$%^&*-_=+"
        while True:
            pwd = "".join(secrets.choice(alphabet) for _ in range(length))
            has_low = any(c.islower() for c in pwd)
            has_up = any(c.isupper() for c in pwd)
            has_dig = any(c.isdigit() for c in pwd)
            has_sym = (not include_symbols) or any(c in "!@#$%^&*-_=+" for c in pwd)
            if has_low and has_up and has_dig and has_sym:
                return pwd

    @staticmethod
    def _to_metadata(rec: dict) -> VaultEntryMetadata:
        return VaultEntryMetadata(
            entry_id=rec["entry_id"],
            label=rec.get("label", ""),
            category=SecretCategory(rec.get("category", "other")),
            host_or_url=rec.get("host_or_url", ""),
            port=rec.get("port"),
            username=rec.get("username", ""),
            has_secret=bool(rec.get("has_secret")),
            has_extra_secret=bool(rec.get("has_extra_secret")),
            masked_preview=rec.get("masked_preview", ""),
            notes="",
            tags=list(rec.get("tags", [])),
            created_at=float(rec.get("created_at", 0.0)),
            updated_at=float(rec.get("updated_at", 0.0)),
        )


password_vault_service = UserPasswordVaultService()
