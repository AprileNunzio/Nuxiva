from __future__ import annotations

import hmac
import hashlib
import secrets

from features.activation.domain.capability_tokens import CapabilityGrant, CapabilityScope


class CapabilitySecurityManager:
    def __init__(self, master_secret: bytes) -> None:
        if len(master_secret) < 32:
            raise ValueError("capability_secret_too_short")
        self._secret = master_secret
        self._active_grants: dict[str, CapabilityGrant] = {}

    def issue_grant(
        self,
        scope: CapabilityScope,
        target_pattern: str,
        ttl_seconds: float,
        max_bytes: int = 1_048_576,
    ) -> str:
        import time
        token_id = secrets.token_hex(16)
        expires_at = time.time() + max(1.0, ttl_seconds)
        grant = CapabilityGrant(
            scope=scope,
            target_pattern=target_pattern,
            expires_at=expires_at,
            max_payload_bytes=max_bytes,
        )
        self._active_grants[token_id] = grant
        signature = hmac.new(self._secret, f"{token_id}:{expires_at}:{scope.value}".encode(), hashlib.sha256).hexdigest()
        return f"{token_id}.{signature}"

    def verify_request(
        self,
        token_str: str,
        scope: CapabilityScope,
        resource: str,
        payload_size: int,
    ) -> bool:
        import time
        parts = token_str.split(".")
        if len(parts) != 2:
            return False
        token_id, signature = parts
        grant = self._active_grants.get(token_id)
        if grant is None:
            return False

        expected_sig = hmac.new(
            self._secret,
            f"{token_id}:{grant.expires_at}:{grant.scope.value}".encode(),
            hashlib.sha256,
        ).hexdigest()

        if not hmac.compare_digest(signature, expected_sig):
            return False

        return grant.allows(scope, resource, payload_size, time.time())
